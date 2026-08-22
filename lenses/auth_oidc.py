"""Optional OIDC / SSO foundation (authorization code + PKCE)."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lenses.shell_actions import client_may_run_shell_actions

_STATE_TTL_SEC = 600
# state -> (expires_at, code_verifier, return_to_path)
_state_store: dict[str, tuple[float, str, str]] = {}


def _truthy_env(name: str) -> bool:
    raw = (os.environ.get(name) or "").strip().lower()
    return raw in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class OidcEnvConfig:
    issuer: str
    client_id: str
    client_secret: str
    redirect_path: str
    scopes: str


def bootstrap_oidc_env_from_workspace(workspace_root: Path) -> None:
    """
    Load ``.lenses-local/lenses-oidc.env`` into the process when keys are not already set.
    Lets production hosts set Google OAuth without systemd env churn.
    """
    p = workspace_root / ".lenses-local" / "lenses-oidc.env"
    if not p.is_file():
        return
    try:
        raw = p.read_text(encoding="utf-8")
    except OSError:
        return
    for line in raw.splitlines():
        chunk = line.strip()
        if not chunk or chunk.startswith("#") or "=" not in chunk:
            continue
        key, _, val = chunk.partition("=")
        key = key.strip()
        if not key or key in os.environ:
            continue
        os.environ[key] = val.strip().strip('"').strip("'")


def client_may_use_oidc_auth(client_ip: str) -> bool:
    """OIDC authorize/callback from browsers (HTTPS stickerboard guests, Studio behind proxy)."""
    if client_may_run_shell_actions(client_ip):
        return True
    return load_oidc_config() is not None


def public_request_origin(
    *,
    host_header: str | None,
    forwarded_proto: str | None = None,
    forwarded_host: str | None = None,
) -> str:
    """
    Canonical browser-facing origin for OAuth redirect URIs.

    Prefer ``LENSES_PUBLIC_ORIGIN`` (e.g. ``https://leo.forgedc.net``) behind reverse proxies.
    """
    explicit = (os.environ.get("LENSES_PUBLIC_ORIGIN") or "").strip().rstrip("/")
    if explicit:
        return explicit
    scheme = (
        "https"
        if (forwarded_proto or "").strip().lower().startswith("https")
        else "http"
    )
    host = (forwarded_host or host_header or "").strip() or "127.0.0.1:8080"
    return f"{scheme}://{host}"


def default_oidc_redirect_path() -> str:
    """OAuth redirect path; use ``/stickerboard/api/…`` when guests are path-mounted."""
    explicit = (os.environ.get("LENSES_OIDC_REDIRECT_PATH") or "").strip()
    if explicit:
        return explicit if explicit.startswith("/") else f"/{explicit}"
    base = (os.environ.get("LENSES_STICKERBOARD_PUBLIC_BASE") or "").strip().rstrip("/")
    if base.endswith("/stickerboard"):
        return "/stickerboard/api/auth/oidc/callback"
    return "/api/auth/oidc/callback"


def load_oidc_config() -> OidcEnvConfig | None:
    """Return config when ``LENSES_OIDC_ISSUER`` and ``LENSES_OIDC_CLIENT_ID`` are set."""
    issuer = (os.environ.get("LENSES_OIDC_ISSUER") or "").strip().rstrip("/")
    cid = (os.environ.get("LENSES_OIDC_CLIENT_ID") or "").strip()
    if not issuer or not cid:
        return None
    secret = (os.environ.get("LENSES_OIDC_CLIENT_SECRET") or "").strip()
    path = default_oidc_redirect_path()
    scopes = (os.environ.get("LENSES_OIDC_SCOPES") or "openid profile email").strip()
    return OidcEnvConfig(
        issuer=issuer,
        client_id=cid,
        client_secret=secret,
        redirect_path=path,
        scopes=scopes,
    )


def fetch_discovery(issuer: str) -> dict[str, Any] | None:
    url = f"{issuer.rstrip('/')}/.well-known/openid-configuration"
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except (urllib.error.URLError, json.JSONDecodeError, OSError):
        return None


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def start_authorize_url(
    *,
    issuer: str,
    client_id: str,
    redirect_uri: str,
    scopes: str,
    return_to: str | None = None,
) -> tuple[str, str, str]:
    """Return (authorize_url, state, code_verifier)."""
    disc = fetch_discovery(issuer)
    if not disc:
        raise RuntimeError("oidc_discovery_failed")
    auth_ep = str(disc.get("authorization_endpoint") or "").strip()
    if not auth_ep:
        raise RuntimeError("missing_authorization_endpoint")

    verifier = _b64url(secrets.token_bytes(48))
    challenge = _b64url(hashlib.sha256(verifier.encode("utf-8")).digest())
    state = _b64url(secrets.token_bytes(24))
    now = time.time()
    rt = (return_to or "").strip()
    if rt and not rt.startswith("/"):
        rt = "/" + rt
    _state_store[state] = (now + _STATE_TTL_SEC, verifier, rt)
    # prune
    dead = [k for k, (exp, _, _) in _state_store.items() if exp < now]
    for k in dead:
        del _state_store[k]

    q = urllib.parse.urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scopes,
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
    )
    return f"{auth_ep}?{q}", state, verifier


def pop_verifier_for_state(state: str) -> tuple[str | None, str]:
    now = time.time()
    hit = _state_store.pop(state, None)
    if not hit:
        return None, ""
    exp, verifier, return_to = hit
    if exp < now:
        return None, ""
    return verifier, (return_to or "").strip()


def resolve_oidc_profile(
    tokens: dict[str, Any], userinfo_endpoint: str | None
) -> dict[str, str] | None:
    """Return login, optional display_name and email from OIDC tokens/userinfo."""
    login = resolve_oidc_login(tokens, userinfo_endpoint)
    if not login:
        return None
    display_name = ""
    email = ""
    id_token = tokens.get("id_token")
    if isinstance(id_token, str) and id_token:
        parts = id_token.split(".")
        if len(parts) >= 2:
            pad = "=" * (-len(parts[1]) % 4)
            try:
                payload = json.loads(
                    base64.urlsafe_b64decode(parts[1] + pad).decode("utf-8", errors="replace")
                )
                if isinstance(payload, dict):
                    display_name = str(
                        payload.get("name") or payload.get("given_name") or ""
                    ).strip()
                    email = str(payload.get("email") or "").strip().lower()
            except (json.JSONDecodeError, OSError, ValueError):
                pass
    access = tokens.get("access_token")
    if isinstance(access, str) and access and userinfo_endpoint:
        req = urllib.request.Request(
            userinfo_endpoint,
            headers={"Authorization": f"Bearer {access}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = resp.read().decode("utf-8")
            ui = json.loads(raw)
            if isinstance(ui, dict):
                if not display_name:
                    display_name = str(
                        ui.get("name") or ui.get("given_name") or ""
                    ).strip()
                if not email:
                    email = str(ui.get("email") or "").strip().lower()
        except (urllib.error.URLError, json.JSONDecodeError, OSError):
            pass
    if not display_name and email:
        display_name = email.split("@", 1)[0]
    out: dict[str, str] = {"login": login}
    if display_name:
        out["display_name"] = display_name[:120]
    if email:
        out["email"] = email[:200]
    return out


def exchange_code_for_tokens(
    *,
    issuer: str,
    token_endpoint: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    code: str,
    code_verifier: str,
) -> dict[str, Any] | None:
    body = urllib.parse.urlencode(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "code_verifier": code_verifier,
        }
    ).encode("utf-8")
    headers: dict[str, str] = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }
    if client_secret:
        basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode("ascii")
        headers["Authorization"] = f"Basic {basic}"
    req = urllib.request.Request(
        token_endpoint,
        data=body,
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            raw = resp.read().decode("utf-8")
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError, OSError):
        return None


def resolve_oidc_login(tokens: dict[str, Any], userinfo_endpoint: str | None) -> str | None:
    """Pick a stable login string for RBAC (``oidc:<sub>`` or email)."""
    id_token = tokens.get("id_token")
    if isinstance(id_token, str) and id_token:
        parts = id_token.split(".")
        if len(parts) >= 2:
            pad = "=" * (-len(parts[1]) % 4)
            try:
                payload = json.loads(
                    base64.urlsafe_b64decode(parts[1] + pad).decode("utf-8", errors="replace")
                )
                if isinstance(payload, dict):
                    sub = str(payload.get("sub") or "").strip()
                    email = str(payload.get("email") or "").strip().lower()
                    if email:
                        return email
                    if sub:
                        return f"oidc:{sub}"
            except (json.JSONDecodeError, OSError, ValueError):
                pass
    access = tokens.get("access_token")
    if isinstance(access, str) and access and userinfo_endpoint:
        req = urllib.request.Request(
            userinfo_endpoint,
            headers={"Authorization": f"Bearer {access}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = resp.read().decode("utf-8")
            ui = json.loads(raw)
            if isinstance(ui, dict):
                sub = str(ui.get("sub") or "").strip()
                email = str(ui.get("email") or "").strip().lower()
                if email:
                    return email
                if sub:
                    return f"oidc:{sub}"
        except (urllib.error.URLError, json.JSONDecodeError, OSError):
            pass
    return None


def oidc_status_payload() -> dict[str, Any]:
    cfg = load_oidc_config()
    if not cfg:
        return {
            "ok": True,
            "configured": False,
            "hint": (
                "Set LENSES_OIDC_ISSUER and LENSES_OIDC_CLIENT_ID in "
                ".lenses-local/lenses-oidc.env (see forge-lenses/docs/examples/"
                "lenses-oidc.env.example), then restart Lenses. For HTTPS hosts set "
                "LENSES_PUBLIC_ORIGIN=https://your-host.example. Register the Google "
                "redirect URI shown in that example for your deployment."
            ),
        }
    disc = fetch_discovery(cfg.issuer)
    return {
        "ok": True,
        "configured": True,
        "issuer": cfg.issuer,
        "discovery_ok": bool(disc),
        "implicit_flow_disabled": True,
        "pkce": True,
        "dev_mode_relaxed_validation": _truthy_env("LENSES_OIDC_DEV_INSECURE"),
    }
