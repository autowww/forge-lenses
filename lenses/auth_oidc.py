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
from typing import Any

_STATE_TTL_SEC = 600
_state_store: dict[str, tuple[float, str]] = {}  # state -> (expires_at, code_verifier)


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


def load_oidc_config() -> OidcEnvConfig | None:
    """Return config when ``LENSES_OIDC_ISSUER`` and ``LENSES_OIDC_CLIENT_ID`` are set."""
    issuer = (os.environ.get("LENSES_OIDC_ISSUER") or "").strip().rstrip("/")
    cid = (os.environ.get("LENSES_OIDC_CLIENT_ID") or "").strip()
    if not issuer or not cid:
        return None
    secret = (os.environ.get("LENSES_OIDC_CLIENT_SECRET") or "").strip()
    path = (os.environ.get("LENSES_OIDC_REDIRECT_PATH") or "/api/auth/oidc/callback").strip()
    if not path.startswith("/"):
        path = "/" + path
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
    _state_store[state] = (now + _STATE_TTL_SEC, verifier)
    # prune
    dead = [k for k, (exp, _) in _state_store.items() if exp < now]
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


def pop_verifier_for_state(state: str) -> str | None:
    now = time.time()
    hit = _state_store.pop(state, None)
    if not hit:
        return None
    exp, verifier = hit
    if exp < now:
        return None
    return verifier


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
            "hint": "Set LENSES_OIDC_ISSUER and LENSES_OIDC_CLIENT_ID (optional LENSES_OIDC_CLIENT_SECRET).",
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
