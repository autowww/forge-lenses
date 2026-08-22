"""GitHub token verification and HttpOnly session store under .lenses-local/."""

from __future__ import annotations

import json
import secrets
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

SESSION_COOKIE = "lenses_session"
SESSION_MAX_AGE_SEC = 8 * 60 * 60


def verify_github_token(token: str) -> tuple[str | None, str | None]:
    """Return (login, error_message)."""
    t = (token or "").strip()
    if not t:
        return None, "missing_token"
    req = urllib.request.Request(
        "https://api.github.com/user",
        headers={
            "Authorization": f"Bearer {t}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "forge-lenses-local/1",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            raw = resp.read().decode("utf-8")
        data = json.loads(raw)
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", errors="replace")[:500]
        except OSError:
            body = ""
        return None, f"github_http_{e.code}: {body}"
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as e:
        return None, str(e)
    login = data.get("login")
    if not isinstance(login, str) or not login.strip():
        return None, "no_login_in_response"
    return login.strip(), None


class SessionManager:
    """File-backed session table (survives restarts); maps session id to GitHub login."""

    def __init__(self, workspace_root: Path) -> None:
        self._dir = workspace_root / ".lenses-local"
        self._path = self._dir / "lenses-sessions.json"
        self._lock = threading.Lock()
        self._sessions: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.is_file():
            return
        try:
            raw = self._path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (OSError, json.JSONDecodeError):
            return
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(k, str) and isinstance(v, dict) and isinstance(v.get("login"), str):
                    row: dict[str, Any] = {"login": v["login"], "at": float(v.get("at", 0))}
                    ap = v.get("auth_provider")
                    if isinstance(ap, str) and ap.strip():
                        row["auth_provider"] = ap.strip()
                    dn = v.get("display_name")
                    if isinstance(dn, str) and dn.strip():
                        row["display_name"] = dn.strip()[:120]
                    em = v.get("email")
                    if isinstance(em, str) and em.strip():
                        row["email"] = em.strip().lower()[:200]
                    self._sessions[k] = row

    def _save_unlocked(self) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".json.tmp")
        payload: dict[str, dict[str, Any]] = {}
        for sid, s in self._sessions.items():
            row = {"login": s["login"], "at": s["at"]}
            ap = s.get("auth_provider")
            if isinstance(ap, str) and ap.strip():
                row["auth_provider"] = ap.strip()
            dn = s.get("display_name")
            if isinstance(dn, str) and dn.strip():
                row["display_name"] = dn.strip()[:120]
            em = s.get("email")
            if isinstance(em, str) and em.strip():
                row["email"] = em.strip().lower()[:200]
            payload[sid] = row
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(self._path)

    def create_session(
        self,
        login: str,
        *,
        auth_provider: str = "github",
        display_name: str | None = None,
        email: str | None = None,
    ) -> str:
        sid = secrets.token_urlsafe(32)
        now = time.time()
        row: dict[str, Any] = {
            "login": login,
            "at": now,
            "auth_provider": (auth_provider or "github").strip() or "github",
        }
        if display_name and str(display_name).strip():
            row["display_name"] = str(display_name).strip()[:120]
        if email and str(email).strip():
            row["email"] = str(email).strip().lower()[:200]
        with self._lock:
            self._sessions[sid] = row
            # prune old
            cutoff = now - SESSION_MAX_AGE_SEC
            dead = [k for k, v in self._sessions.items() if v.get("at", 0) < cutoff]
            for k in dead:
                del self._sessions[k]
            self._save_unlocked()
        return sid

    def session_login(self, session_id: str | None) -> str | None:
        if not session_id:
            return None
        with self._lock:
            s = self._sessions.get(session_id)
            if not s:
                return None
            if time.time() - float(s.get("at", 0)) > SESSION_MAX_AGE_SEC:
                del self._sessions[session_id]
                self._save_unlocked()
                return None
            return str(s.get("login", "")) or None

    def session_profile(self, session_id: str | None) -> dict[str, str] | None:
        if not session_id:
            return None
        with self._lock:
            s = self._sessions.get(session_id)
            if not s:
                return None
            if time.time() - float(s.get("at", 0)) > SESSION_MAX_AGE_SEC:
                return None
            login = str(s.get("login", "")) or ""
            out: dict[str, str] = {"login": login}
            dn = s.get("display_name")
            if isinstance(dn, str) and dn.strip():
                out["display_name"] = dn.strip()
            em = s.get("email")
            if isinstance(em, str) and em.strip():
                out["email"] = em.strip().lower()
            return out

    def session_auth_provider(self, session_id: str | None) -> str | None:
        if not session_id:
            return None
        with self._lock:
            s = self._sessions.get(session_id)
            if not s:
                return None
            if time.time() - float(s.get("at", 0)) > SESSION_MAX_AGE_SEC:
                return None
            ap = s.get("auth_provider")
            return str(ap).strip() if isinstance(ap, str) and ap.strip() else "github"

    def clear_session(self, session_id: str | None) -> None:
        if not session_id:
            return
        with self._lock:
            self._sessions.pop(session_id, None)
            self._save_unlocked()
