"""WBS management: list all workspace projects, create WBS.md from blueprint template, optional git tags."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from lenses.scan import resolve_workspace_child_dir

# Conservative tag names (avoid shell / path injection via git)
_TAG_RE = re.compile(r"^[A-Za-z0-9._\-/+]+$")
_MAX_TAG_LEN = 200

# When blueprints submodule is missing, minimal starter (same headings as blueprint template).
_FALLBACK_WBS_TEMPLATE = """# Work breakdown structure — [Product / Initiative Name]

## 1. Overview

| Field | Detail |
|-------|--------|
| **Product / initiative** | |
| **Product Spark / Milestone** | |
| **Delivery approach** | PoC / MVP / Phase |
| **Owner** | |
| **Date** | YYYY-MM-DD |
| **Status** | Draft / Baselined / Updated |

---

## 2. Themes

| Theme ID | Theme | Strategic objective / OKR |
|----------|-------|--------------------------|
| T1 | | |
| T2 | | |

---

## 3. WBS hierarchy

### Theme: T1 — [Theme Name]

#### Epic: M1E1 — [Epic Name]

| Story ID | Story | Acceptance criteria (summary) | Priority | Estimate | Dependencies |
|----------|-------|------------------------------|----------|----------|-------------|
| M1E1S1 | | | High / Medium / Low | S / M / L | |

**Tasks**

| Task ID | Task | Story | Phase prefix | Estimate (hrs) |
|---------|------|-------|-------------|----------------|
| M1E1S1T1 | | M1E1S1 | `discover:` / `specify:` / `design:` / `build:` / `verify:` / `release:` | |

---

*Last updated: YYYY-MM-DD · Owner: [name/role]*
"""


def load_wbs_template(lenses_repo_root: Path) -> str:
    p = lenses_repo_root / "blueprints" / "pdlc" / "templates" / "WBS.template.md"
    if p.is_file():
        try:
            return p.read_text(encoding="utf-8")
        except OSError:
            pass
    return _FALLBACK_WBS_TEMPLATE


def validate_tag_name(tag: str) -> bool:
    t = tag.strip()
    if not t or len(t) > _MAX_TAG_LEN:
        return False
    return bool(_TAG_RE.match(t))


def prepare_wbs_body(
    template: str,
    product_title: str,
    *,
    baseline_release: str | None,
    today: str | None = None,
) -> str:
    day = today or date.today().isoformat()
    body = template.replace("\r\n", "\n")
    body = re.sub(
        r"^# Work breakdown structure — .+$",
        f"# Work breakdown structure — {product_title}",
        body,
        count=1,
        flags=re.MULTILINE,
    )
    body = re.sub(
        r"^\| \*\*Product / initiative\*\* \| \|",
        f"| **Product / initiative** | {product_title} |",
        body,
        count=1,
        flags=re.MULTILINE,
    )
    body = re.sub(
        r"^\| \*\*Date\*\* \| YYYY-MM-DD \|",
        f"| **Date** | {day} |",
        body,
        count=1,
        flags=re.MULTILINE,
    )
    if baseline_release and "**Release baseline**" not in body:
        body = body.replace(
            "| **Status** | Draft / Baselined / Updated |",
            "| **Status** | Draft / Baselined / Updated |\n"
            f"| **Release baseline** | {baseline_release} |",
            1,
        )
    body = re.sub(
        r"\*Last updated: YYYY-MM-DD",
        f"*Last updated: {day}",
        body,
        count=1,
    )
    return body


def _run_git(repo: Path, *args: str, timeout: float = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def git_current_branch(repo: Path) -> str:
    r = _run_git(repo, "branch", "--show-current", timeout=10)
    if r.returncode != 0:
        return ""
    return (r.stdout or "").strip()


def list_git_tags(repo: Path, *, limit: int = 100) -> list[str]:
    try:
        r = _run_git(repo, "tag", "--sort=-creatordate", timeout=20)
        if r.returncode != 0:
            return []
        out = [ln.strip() for ln in (r.stdout or "").splitlines() if ln.strip()]
        return out[:limit]
    except (OSError, subprocess.TimeoutExpired):
        return []


def git_tag_exists(repo: Path, tag: str) -> bool:
    r = _run_git(repo, "rev-parse", "--verify", f"refs/tags/{tag}", timeout=10)
    return r.returncode == 0


def git_create_annotated_tag(repo: Path, tag: str, message: str) -> dict[str, Any]:
    if not validate_tag_name(tag):
        return {"ok": False, "error": "invalid_tag", "stderr": "", "stdout": ""}
    try:
        r = _run_git(
            repo,
            "tag",
            "-a",
            tag,
            "-m",
            message,
            timeout=60,
        )
        return {
            "ok": r.returncode == 0,
            "error": "" if r.returncode == 0 else "tag_failed",
            "stdout": r.stdout or "",
            "stderr": r.stderr or "",
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout", "stdout": "", "stderr": ""}
    except OSError as exc:
        return {"ok": False, "error": str(exc), "stdout": "", "stderr": ""}


WORKSPACE_PROJECT_KEY = "__workspace__"


@dataclass
class WbsProjectRow:
    key: str
    label: str
    wbs_entries: list[dict[str, Any]]


def partition_wbs_by_project(state: dict[str, Any]) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    child_names = {
        str(c.get("name", "")).strip()
        for c in (state.get("children") or [])
        if isinstance(c, dict) and str(c.get("name", "")).strip()
    }
    by_hint: dict[str, list[dict[str, Any]]] = {}
    workspace_docs: list[dict[str, Any]] = []
    for w in state.get("wbs") or []:
        if not isinstance(w, dict):
            continue
        h = str(w.get("repo_hint", "")).strip()
        if h == "docs" and "docs" not in child_names:
            workspace_docs.append(w)
        else:
            by_hint.setdefault(h, []).append(w)
    return by_hint, workspace_docs


def build_wbs_project_rows(state: dict[str, Any]) -> list[WbsProjectRow]:
    by_hint, workspace_docs = partition_wbs_by_project(state)
    rows: list[WbsProjectRow] = []
    if workspace_docs:
        rows.append(
            WbsProjectRow(
                key=WORKSPACE_PROJECT_KEY,
                label="Workspace (root)",
                wbs_entries=workspace_docs,
            )
        )
    children_sorted = sorted(
        (c for c in (state.get("children") or []) if isinstance(c, dict)),
        key=lambda x: str(x.get("name", "")).lower(),
    )
    for c in children_sorted:
        name = str(c.get("name", "")).strip()
        if not name:
            continue
        rows.append(
            WbsProjectRow(
                key=name,
                label=name,
                wbs_entries=by_hint.get(name, []),
            )
        )
    return rows


def resolve_wbs_project_base(
    workspace_root: Path,
    registry: dict[str, Any] | None,
    project_key: str,
) -> Path | None:
    if project_key == WORKSPACE_PROJECT_KEY:
        return workspace_root.resolve()
    return resolve_workspace_child_dir(workspace_root, project_key, registry)


def wbs_md_exists(base: Path) -> bool:
    return (base / "docs" / "requirements" / "WBS.md").is_file()


def build_wbs_management_payload(
    workspace_root: Path,
    registry: dict[str, Any] | None,
    state: dict[str, Any],
) -> dict[str, Any]:
    """JSON-serializable overview for /api/wbs-management."""
    rows = build_wbs_project_rows(state)
    out: list[dict[str, Any]] = []
    for row in rows:
        base = resolve_wbs_project_base(workspace_root, registry, row.key)
        tags: list[str] = []
        branch = ""
        is_git = False
        if base is not None:
            git_dir = base / ".git"
            is_git = git_dir.exists() and (git_dir.is_dir() or git_dir.is_file())
            if is_git:
                tags = list_git_tags(base)
                branch = git_current_branch(base)
        wbs_list = []
        for w in row.wbs_entries:
            wbs_list.append(
                {
                    "rel_path": str(w.get("rel_path", "")),
                    "kind": str(w.get("kind", "")),
                    "repo_hint": str(w.get("repo_hint", "")),
                }
            )
        out.append(
            {
                "key": row.key,
                "label": row.label,
                "is_git": is_git,
                "branch": branch,
                "tags": tags,
                "wbs": wbs_list,
                "has_wbs_md": wbs_md_exists(base) if base else False,
            }
        )
    return {"projects": out}


def create_wbs_md(
    workspace_root: Path,
    registry: dict[str, Any] | None,
    lenses_repo_root: Path,
    project_key: str,
    *,
    baseline_tag: str | None,
    new_tag: str | None,
) -> dict[str, Any]:
    """Create docs/requirements/WBS.md; optionally record baseline tag in doc; optionally git tag."""
    base = resolve_wbs_project_base(workspace_root, registry, project_key)
    if base is None:
        return {"ok": False, "error": "unknown_project"}
    req = base / "docs" / "requirements"
    target = req / "WBS.md"
    if target.is_file():
        return {"ok": False, "error": "wbs_md_already_exists"}
    baseline = (baseline_tag or "").strip() or None
    if baseline and not validate_tag_name(baseline):
        return {"ok": False, "error": "invalid_baseline_tag"}
    new_t = (new_tag or "").strip() or None
    if new_t:
        if not validate_tag_name(new_t):
            return {"ok": False, "error": "invalid_new_tag"}
        if not (base / ".git").exists():
            return {"ok": False, "error": "not_a_git_repo_for_tag"}
    tpl = load_wbs_template(lenses_repo_root)
    title = "Workspace" if project_key == WORKSPACE_PROJECT_KEY else project_key
    body = prepare_wbs_body(
        tpl,
        title,
        baseline_release=baseline,
    )
    try:
        req.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    except OSError as exc:
        return {"ok": False, "error": "write_failed", "detail": str(exc)}
    rel = str(target.resolve().relative_to(workspace_root.resolve())).replace("\\", "/")
    result: dict[str, Any] = {
        "ok": True,
        "rel_path": rel,
        "tag_created": False,
        "tag_warning": None,
    }
    if new_t:
        git_dir = base / ".git"
        if git_dir.exists():
            if git_tag_exists(base, new_t):
                result["tag_warning"] = "tag_already_exists"
            else:
                msg = f"Release tag for WBS baseline ({title})"
                tr = git_create_annotated_tag(base, new_t, msg)
                if tr.get("ok"):
                    result["tag_created"] = True
                else:
                    result["tag_warning"] = tr.get("error") or "tag_failed"
                    result["tag_stderr"] = tr.get("stderr", "")
    return result
