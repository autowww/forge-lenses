"""Heuristic agentic / coding-standards compliance signals per repository (filesystem + light git).

Aligned with blueprint themes in ``agentic-coding-standards`` — not a formal audit.
"""

from __future__ import annotations

import html
import subprocess
from pathlib import Path
from typing import Any

# Stable check ids for registry ignore lists
CHECK_DEFS: list[dict[str, Any]] = [
    {
        "id": "ci_config",
        "label": "CI / automation config",
        "weight": 22,
        "theme": "verification",
    },
    {
        "id": "contributing_or_docs",
        "label": "CONTRIBUTING or docs entry",
        "weight": 16,
        "theme": "intent",
    },
    {
        "id": "sdlc_or_blueprints",
        "label": "sdlc/ or blueprints/ workspace",
        "weight": 12,
        "theme": "intent",
    },
    {
        "id": "cursor_agentic",
        "label": ".cursor rules or skills",
        "weight": 10,
        "theme": "agentic",
    },
    {
        "id": "forge_artifacts",
        "label": "Forge paths (forge/, forge-logs/, ember-logs/)",
        "weight": 8,
        "theme": "forge",
    },
    {
        "id": "dependency_visibility",
        "label": "Dependency lockfile or manifest visibility",
        "weight": 12,
        "theme": "security",
    },
    {
        "id": "deploy_surface",
        "label": "Deploy config (firebase.json)",
        "weight": 6,
        "theme": "verification",
    },
    {
        "id": "attribution_sample",
        "label": "Recent commits mention AI / co-author markers",
        "weight": 8,
        "theme": "attribution",
    },
]


def _run_git_log_body(cwd: Path, n: int = 24) -> str:
    try:
        r = subprocess.run(
            ["git", "-C", str(cwd), "log", f"-{n}", "--pretty=format:%B%n---LENSES---"],
            capture_output=True,
            text=True,
            timeout=15.0,
        )
        if r.returncode != 0:
            return ""
        return r.stdout or ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def _has_ci(repo: Path) -> tuple[str, str]:
    gh = repo / ".github" / "workflows"
    if gh.is_dir():
        for p in gh.iterdir():
            if p.is_file() and p.suffix.lower() in (".yml", ".yaml"):
                return "pass", f"Found {p.name}"
    for name in (".gitlab-ci.yml", "Jenkinsfile", "azure-pipelines.yml", ".circleci"):
        p = repo / name
        if p.is_file():
            return "pass", f"Found {name}"
    circle = repo / ".circleci" / "config.yml"
    if circle.is_file():
        return "pass", "Found .circleci/config.yml"
    return "warn", "No common CI entrypoint (.github/workflows, GitLab, Jenkins, …)"


def _has_contributing_docs(repo: Path) -> tuple[str, str]:
    if (repo / "CONTRIBUTING.md").is_file():
        return "pass", "CONTRIBUTING.md present"
    docs = repo / "docs"
    if docs.is_dir():
        for leaf in ("index.html", "README.md", "index.md"):
            if (docs / leaf).is_file():
                return "pass", f"docs/{leaf} present"
    return "warn", "Add CONTRIBUTING.md or docs/index (html/md) for contributor intent"


def _sdlc_blueprints(repo: Path) -> tuple[str, str]:
    parts = []
    if (repo / "sdlc").is_dir():
        parts.append("sdlc/")
    if (repo / "blueprints").is_dir():
        parts.append("blueprints/")
    if parts:
        return "pass", ", ".join(parts)
    return "warn", "No sdlc/ or blueprints/ — link specs/process to the repo"


def _cursor_hygiene(repo: Path) -> tuple[str, str]:
    cur = repo / ".cursor"
    if not cur.is_dir():
        return "warn", "No .cursor/ — optional Cursor rules/skills for agentic norms"
    if (cur / "rules").is_dir() or (cur / "skills").is_dir():
        return "pass", ".cursor/rules or .cursor/skills present"
    return "warn", ".cursor exists but no rules/ or skills/ subfolder"


def _forge_paths(repo: Path) -> tuple[str, str]:
    hits = []
    for name in ("forge", "forge-logs", "ember-logs"):
        if (repo / name).is_dir():
            hits.append(f"{name}/")
    if hits:
        return "pass", ", ".join(hits)
    return "warn", "No forge/, forge-logs/, or ember-logs/ (skip if not using Forge)"


def _dependency_visibility(repo: Path) -> tuple[str, str, bool]:
    """Returns (status, detail, applicable)."""
    root_files = {p.name for p in repo.iterdir() if p.is_file()}
    manifests = []
    if "package.json" in root_files:
        manifests.append("npm")
    if "Cargo.toml" in root_files:
        manifests.append("rust")
    if "go.mod" in root_files:
        manifests.append("go")
    if "pyproject.toml" in root_files or "setup.py" in root_files:
        manifests.append("python")

    locks = (
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "npm-shrinkwrap.json",
        "Cargo.lock",
        "poetry.lock",
        "uv.lock",
        "Pipfile.lock",
        "go.sum",
    )
    has_lock = any((repo / f).is_file() for f in locks)
    if "requirements.txt" in root_files:
        has_lock = True  # visibility, not strict lock

    if not manifests:
        return "na", "No root package manifest at repo root", False

    if has_lock:
        return "pass", "Lockfile or requirements.txt present", True
    return "warn", "Add a lockfile (or requirements.txt) for reproducible deps", True


def _firebase(repo: Path) -> tuple[str, str, bool]:
    if (repo / "firebase.json").is_file():
        return "pass", "firebase.json present (deploy surface)", True
    return "na", "No firebase.json — not a Firebase-hosted repo", False


def _attribution_sample(repo: Path, *, enabled: bool) -> tuple[str, str, bool]:
    if not enabled:
        return "na", "Commit-body scan disabled (default off)", False
    body = _run_git_log_body(repo, 24)
    if not body.strip():
        return "warn", "Could not read recent commit messages", True
    low = body.lower()
    patterns = (
        "co-authored-by",
        "🤖",
        "generated with",
        "ai-assisted",
        "copilot",
    )
    if any(p in low for p in patterns):
        return "pass", "Recent messages include attribution / AI markers", True
    return "warn", "No obvious AI/co-author markers in last ~24 commits — document AI use in PRs", True


def _status_points(status: str) -> float:
    if status == "pass":
        return 1.0
    if status == "warn":
        return 0.45
    if status == "na":
        return 1.0  # does not hurt score when excluded from denominator
    return 0.0


def compliance_report(
    repo_path: Path,
    *,
    registry: dict[str, Any],
    project_name: str,
    scan_commit_messages: bool = False,
) -> dict[str, Any]:
    """Return JSON-serializable compliance report for one workspace child."""
    env_scan = __import__("os").environ.get("LENSES_STANDARDS_SCAN_COMMITS", "")
    scan_commits = scan_commit_messages or env_scan.lower() in ("1", "true", "yes")

    global_ignore = set(registry.get("standards_compliance_ignore_checks") or [])
    per_proj = registry.get("standards_compliance_overrides") or {}
    if isinstance(per_proj, dict) and project_name in per_proj:
        extra = per_proj[project_name].get("ignore_checks") or []
        global_ignore |= set(extra)

    rp = repo_path.resolve()
    is_git = (rp / ".git").exists()

    runners: dict[str, Any] = {
        "ci_config": lambda: _has_ci(rp),
        "contributing_or_docs": lambda: _has_contributing_docs(rp),
        "sdlc_or_blueprints": lambda: _sdlc_blueprints(rp),
        "cursor_agentic": lambda: _cursor_hygiene(rp),
        "forge_artifacts": lambda: _forge_paths(rp),
        "dependency_visibility": lambda: _dependency_visibility(rp),
        "deploy_surface": lambda: _firebase(rp),
        "attribution_sample": lambda: _attribution_sample(rp, enabled=scan_commits and is_git),
    }

    checks_out: list[dict[str, Any]] = []
    weights_num = 0.0
    weights_den = 0.0

    for d in CHECK_DEFS:
        cid = d["id"]
        if cid in global_ignore:
            checks_out.append(
                {
                    "id": cid,
                    "label": d["label"],
                    "theme": d["theme"],
                    "weight": d["weight"],
                    "status": "skipped",
                    "detail": "Ignored via registry",
                    "suggestion": "",
                }
            )
            continue

        if not is_git and cid == "attribution_sample":
            checks_out.append(
                {
                    "id": cid,
                    "label": d["label"],
                    "theme": d["theme"],
                    "weight": d["weight"],
                    "status": "na",
                    "detail": "Not a git repository",
                    "suggestion": "",
                }
            )
            continue

        fn = runners[cid]
        raw = fn()
        if len(raw) == 3:
            status, detail, applicable = raw
        else:
            status, detail = raw  # type: ignore[misc]
            applicable = True

        if status == "na" or not applicable:
            checks_out.append(
                {
                    "id": cid,
                    "label": d["label"],
                    "theme": d["theme"],
                    "weight": d["weight"],
                    "status": "na",
                    "detail": detail,
                    "suggestion": "",
                }
            )
            continue

        w = float(d["weight"])
        weights_den += w
        weights_num += w * _status_points(status)

        suggestion = ""
        if status == "warn":
            suggestion = detail

        checks_out.append(
            {
                "id": cid,
                "label": d["label"],
                "theme": d["theme"],
                "weight": d["weight"],
                "status": status,
                "detail": detail,
                "suggestion": suggestion,
            }
        )

    score = 0
    if weights_den > 0:
        score = int(round(100.0 * (weights_num / weights_den)))
    tier = "minimal"
    if score >= 85:
        tier = "good"
    elif score >= 55:
        tier = "partial"

    suggestions = [c["suggestion"] for c in checks_out if c.get("suggestion")]
    summary = f"Score {score}/100 ({tier}) — heuristic signals only; not an audit."

    return {
        "score": score,
        "tier": tier,
        "summary": summary,
        "checks": checks_out,
        "suggestions": suggestions,
        "is_git": is_git,
    }


def enrich_workspace_with_standards(state: dict[str, Any], registry: dict[str, Any]) -> None:
    """Mutate ``state`` in place: each child dict gets ``standards_compliance``."""
    children = state.get("children")
    if not isinstance(children, list):
        return
    for ch in children:
        if not isinstance(ch, dict):
            continue
        name = str(ch.get("name", "")).strip()
        path_s = str(ch.get("path", "")).strip()
        if not name or not path_s:
            continue
        rp = Path(path_s)
        try:
            ch["standards_compliance"] = compliance_report(
                rp, registry=registry, project_name=name
            )
        except OSError:
            ch["standards_compliance"] = {
                "score": 0,
                "tier": "minimal",
                "summary": "Could not read repository path.",
                "checks": [],
                "suggestions": [],
                "is_git": False,
            }
    state["standards_compliance_note"] = (
        "Heuristic proxy checks for agentic coding norms (filesystem + optional git). "
        "Not a compliance audit. See blueprint: agentic-coding-standards."
    )


def svg_compliance_score_bars(
    rows: list[tuple[str, int]],
    *,
    width: int = 680,
    row_height: int = 26,
    label_width: int = 168,
    margin_r: int = 48,
) -> str:
    """Horizontal bars for standards score 0–100 per repository name."""
    if not rows:
        return '<p class="forge-support mb-0">No repositories to score.</p>'
    vmax = 100
    n = len(rows)
    height = 28 + n * row_height
    inner_w = width - label_width - margin_r - 16
    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'role="img" aria-label="Standards compliance score by repository" '
        f'style="width:100%;max-width:{width}px;height:auto">',
        '<rect width="100%" height="100%" fill="transparent"/>',
    ]
    for i, (name, v) in enumerate(rows):
        v = max(0, min(100, int(v)))
        y = 20 + i * row_height
        label = html.escape(name[:48], quote=True)
        color = "rgba(34,197,94,0.85)" if v >= 85 else ("rgba(245,158,11,0.88)" if v >= 55 else "rgba(239,68,68,0.75)")
        parts.append(
            f'<text x="4" y="{y + 14}" fill="var(--forge-muted,#94a3b8)" font-size="11" '
            f'text-anchor="start">{label}</text>'
        )
        bw = (v / vmax) * inner_w if vmax else 0
        bw = max(bw, 1.0) if v > 0 else 0
        x0 = label_width
        parts.append(
            f'<rect x="{x0:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{row_height - 8:.1f}" '
            f'fill="{color}" rx="3"><title>{label}: {v}/100</title></rect>'
        )
        parts.append(
            f'<text x="{x0 + inner_w + 6:.1f}" y="{y + 14}" fill="var(--forge-muted,#94a3b8)" '
            f'font-size="11" text-anchor="start">{v}</text>'
        )
    parts.append("</svg>")
    return "\n".join(parts)
