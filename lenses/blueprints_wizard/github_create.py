"""Create a GitHub repository from wizard draft metadata (experimental)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from lenses.blueprints_wizard.schemas import WizardSessionDocument, normalize_wizard_payload
from lenses.blueprints_wizard.session_store import load_session, save_session_replace, validate_session_id


def _github_token() -> str:
    return (os.environ.get("LENSES_GITHUB_TOKEN") or os.environ.get("GITHUB_TOKEN") or "").strip()


def create_github_repo_http(
    *,
    token: str,
    repo_name: str,
    description: str,
    private: bool,
    owner: str,
    account_type: str,
) -> dict[str, Any]:
    """
    Call GitHub REST API. Returns {"ok": True, "html_url": str} or {"ok": False, "error": str, ...}.
    """
    name = repo_name.strip()
    if not name:
        return {"ok": False, "error": "missing_repo_name"}
    if not token:
        return {"ok": False, "error": "missing_github_token"}
    own = owner.strip()
    at = account_type.strip().lower()
    if at == "org":
        if not own:
            return {"ok": False, "error": "missing_owner"}
        url = f"https://api.github.com/orgs/{urllib.parse.quote(own)}/repos"
    else:
        url = "https://api.github.com/user/repos"
    body_obj: dict[str, Any] = {
        "name": name,
        "description": (description or "")[:350],
        "private": private,
        "auto_init": True,
    }
    data = json.dumps(body_obj).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "forge-lenses-blueprints-wizard",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            parsed = json.loads(raw)
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8", errors="replace")[:2000]
        except OSError:
            pass
        return {"ok": False, "error": "github_http_error", "status": e.code, "detail": detail}
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as e:
        return {"ok": False, "error": "github_request_failed", "detail": str(e)}
    html_url = parsed.get("html_url")
    if isinstance(html_url, str) and html_url.startswith("http"):
        return {"ok": True, "html_url": html_url}
    return {"ok": False, "error": "github_unexpected_response"}


def post_create_repo(
    workspace_root: Path,
    session_id: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    """
    Create remote repo from session new_product_draft; store created_repo_url on success.
    Body must include confirm: true.
    """
    if not validate_session_id(session_id):
        return {"ok": False, "error": "invalid_session_id"}
    confirm = body.get("confirm")
    if confirm is not True and str(confirm).lower() not in ("1", "true", "yes"):
        return {"ok": False, "error": "confirmation_required"}
    doc = load_session(workspace_root, session_id)
    if doc is None:
        return {"ok": False, "error": "not_found"}
    pl = normalize_wizard_payload(doc.payload)
    nd = pl.get("new_product_draft")
    if not isinstance(nd, dict):
        return {"ok": False, "error": "invalid_new_product_draft"}
    repo_name = str(nd.get("repo_name", "")).strip()
    visibility = str(nd.get("visibility", "private")).lower()
    private = visibility != "public"
    description = str(nd.get("description", ""))
    owner = str(nd.get("owner", "")).strip()
    account_type = str(nd.get("account_type", "user")).strip().lower()
    token = _github_token()
    gh = create_github_repo_http(
        token=token,
        repo_name=repo_name,
        description=description,
        private=private,
        owner=owner,
        account_type=account_type,
    )
    if not gh.get("ok"):
        return gh
    html_url = str(gh.get("html_url", ""))
    d = doc.to_dict()
    pl2 = normalize_wizard_payload(d["payload"])
    pl2["created_repo_url"] = html_url
    d["payload"] = pl2
    ok_save, err_save = save_session_replace(workspace_root, session_id, d)
    if not ok_save:
        return {
            "ok": False,
            "error": "repo_created_but_session_not_saved",
            "html_url": html_url,
            "save_error": err_save,
        }
    loaded = load_session(workspace_root, session_id)
    return {"ok": True, "html_url": html_url, "session": loaded.to_dict() if loaded else d}

