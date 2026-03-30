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

# Curated rationale and Cursor prompts (static; not a vector RAG). Placeholders: {project_name}, {repo_path}
CHECK_GUIDANCE: dict[str, dict[str, str]] = {
    "ci_config": {
        "rationale": (
            "Continuous integration catches regressions before merge and gives agents a single "
            "definition of “green.” Without it, AI-generated changes can drift silently. A workflow "
            "file also documents how to build and test the project for humans and tools."
        ),
        "prompt_warn": (
            "In the repository at {repo_path} (project name: {project_name}), add a minimal CI "
            "entrypoint so every push or pull request runs build and tests. Create `.github/workflows/ci.yml` "
            "(GitHub Actions) that checks out the repo, installs dependencies for this stack (detect from "
            "manifests: package.json, pyproject.toml, Cargo.toml, go.mod, etc.), and runs the project’s "
            "standard test or lint command. Use a matrix only if the project genuinely needs multiple "
            "versions. Keep the workflow minimal and documented with a short comment at the top."
        ),
        "prompt_pass": (
            "CI is present. Review `.github/workflows/` or your GitLab/Jenkins config at {repo_path}: "
            "ensure the workflow runs on pull_request and push to the default branch, fails on test "
            "failure, and optionally add a job that runs formatting or typecheck if the stack supports it."
        ),
        "prompt_na": "",
        "prompt_skipped": "",
    },
    "contributing_or_docs": {
        "rationale": (
            "CONTRIBUTING or a docs entry signals intent: how to run, test, and propose changes. "
            "That reduces ambiguity for contributors and for agents that need repo-specific conventions."
        ),
        "prompt_warn": (
            "At repository root {repo_path} ({project_name}), add either `CONTRIBUTING.md` or a "
            "`docs/` folder with `index.md`, `README.md`, or `index.html` describing how to set up "
            "the dev environment, run tests, open PRs, and any code style or commit conventions. "
            "Keep it short (one screen) and link to deeper docs if needed."
        ),
        "prompt_pass": (
            "Docs entry exists. Skim CONTRIBUTING or docs/ at {repo_path} and add a short “Agent / "
            "automation” section if missing: how to run the full test suite and where SDLC or blueprint "
            "content lives."
        ),
        "prompt_na": "",
        "prompt_skipped": "",
    },
    "sdlc_or_blueprints": {
        "rationale": (
            "An `sdlc/` or `blueprints/` tree ties the codebase to process and specifications, "
            "which helps agents align changes with methodology and traceability expectations."
        ),
        "prompt_warn": (
            "Under {repo_path} ({project_name}), add a `sdlc/` and/or `blueprints/` directory (even "
            "as a git submodule pointer) and a short README explaining how this repo relates to SDLC "
            "or blueprint content. If the process lives elsewhere, add a `docs/` link file that points "
            "to the canonical handbook URL."
        ),
        "prompt_pass": (
            "sdlc/ or blueprints/ is present. At {repo_path}, verify README or docs link to the "
            "active process sources and update submodule pins if this repo embeds blueprints."
        ),
        "prompt_na": "",
        "prompt_skipped": "",
    },
    "cursor_agentic": {
        "rationale": (
            "`.cursor/rules` and `.cursor/skills` encode team norms for the editor: testing, commits, "
            "and boundaries for AI-assisted work. They are optional but improve repeatability across machines."
        ),
        "prompt_warn": (
            "At {repo_path} ({project_name}), add `.cursor/rules/` with at least one `.mdc` rule file "
            "(or `.cursor/skills/` with SKILL.md files) that states: test commands to run before commit, "
            "one-commit-per-project boundaries if applicable, and links to your agentic coding standards. "
            "If `.cursor` exists but has no rules/skills, create `rules/workspace.mdc` with those norms."
        ),
        "prompt_pass": (
            "Cursor rules or skills exist. Review `.cursor/rules` and `.cursor/skills` under {repo_path} "
            "for drift: add a rule referencing your blueprint for agentic coding standards if not already there."
        ),
        "prompt_na": "",
        "prompt_skipped": "",
    },
    "forge_artifacts": {
        "rationale": (
            "Forge-oriented folders (`forge/`, `forge-logs/`, `ember-logs/`) indicate local workflow "
            "artifacts and logs. They help correlate agent runs with repository state; skip if you do not use Forge."
        ),
        "prompt_warn": (
            "If this project uses Forge SDLC workflows, under {repo_path} ({project_name}) create the "
            "expected directories (e.g. `forge/`, `forge-logs/`, or `ember-logs/`) and add a one-line "
            "`.gitignore` or README note for what belongs there. If you do not use Forge, document that "
            "in README so this heuristic can be ignored."
        ),
        "prompt_pass": (
            "Forge paths detected. Confirm {repo_path} documents what is written under forge*/ember-logs "
            "and that large or sensitive log files are gitignored appropriately."
        ),
        "prompt_na": "",
        "prompt_skipped": "",
    },
    "dependency_visibility": {
        "rationale": (
            "Lockfiles or pinned requirements make installs reproducible for CI and for anyone replaying "
            "an agent’s environment. Without them, “works on my machine” and supply-chain drift increase."
        ),
        "prompt_warn": (
            "At {repo_path} ({project_name}), add a lockfile appropriate to your manifest: "
            "`package-lock.json` or `pnpm-lock.yaml` / `yarn.lock` for npm; `Cargo.lock` for Rust; "
            "`poetry.lock` or `uv.lock` for Python; `go.sum` for Go. Commit it. If you intentionally use "
            "`requirements.txt` only, ensure it pins versions or use a lock tool."
        ),
        "prompt_pass": (
            "Lockfile or requirements present. Periodically refresh dependencies at {repo_path} and "
            "ensure CI installs from the lockfile with `npm ci` / `pip install -r` / equivalent."
        ),
        "prompt_na": (
            "No lockfile prompt applies until a root manifest exists (package.json, pyproject.toml, etc.). "
            "When you add one, add the matching lockfile in the same commit."
        ),
        "prompt_skipped": "",
    },
    "deploy_surface": {
        "rationale": (
            "`firebase.json` (when present) signals a defined deploy surface for static hosting. "
            "It helps agents and humans know where production output is published."
        ),
        "prompt_warn": (
            "If this repo deploys to Firebase Hosting, add `firebase.json` at {repo_path} ({project_name}) "
            "with public directory and ignore rules aligned with your build output. If deployment is elsewhere, "
            "document the deploy command and target in README."
        ),
        "prompt_pass": (
            "firebase.json present. Verify hosting targets and predeploy hooks at {repo_path} match your "
            "actual build directory."
        ),
        "prompt_na": (
            "This repo does not use Firebase Hosting; no firebase.json is expected. If you adopt Firebase later, "
            "add firebase.json and document predeploy in README."
        ),
        "prompt_skipped": "",
    },
    "attribution_sample": {
        "rationale": (
            "Commit messages that mention AI assistance or co-authors improve transparency and auditability. "
            "Heuristic scan of recent messages is optional and off by default."
        ),
        "prompt_warn": (
            "For {repo_path} ({project_name}), adopt a short convention in CONTRIBUTING or PR template: "
            "when a change is AI-assisted, add a trailer like `Co-authored-by: Name <email>` or a line in "
            "the PR body. Optionally enable Lenses commit-body scan via environment or registry if you want "
            "this check to score commits."
        ),
        "prompt_pass": (
            "Recent commits show attribution markers. Keep documenting AI use in PRs at {repo_path}; "
            "extend patterns if your team uses different wording."
        ),
        "prompt_na": (
            "Commit-body scan is disabled or not applicable (non-git repo). To enable scoring, use a git "
            "repo and set `LENSES_STANDARDS_SCAN_COMMITS=1` or enable via registry when supported."
        ),
        "prompt_skipped": "",
    },
}


def _enrich_checks_with_guidance(
    checks: list[dict[str, Any]],
    *,
    project_name: str,
    repo_path: Path,
) -> None:
    """Attach ``rationale`` and ``cursor_fix_prompt`` to each check dict in place."""
    ctx = {"project_name": project_name, "repo_path": str(repo_path.resolve())}
    for c in checks:
        cid = c.get("id")
        if not isinstance(cid, str):
            continue
        g = CHECK_GUIDANCE.get(cid, {})
        rationale_t = g.get(
            "rationale",
            "This check reflects a heuristic signal for agentic coding hygiene; see the blueprint for methodology.",
        )
        try:
            c["rationale"] = rationale_t.format(**ctx)
        except (KeyError, ValueError):
            c["rationale"] = rationale_t

        st = str(c.get("status", ""))
        key = "prompt_warn"
        if st == "pass":
            key = "prompt_pass"
        elif st == "na":
            key = "prompt_na"
        elif st == "skipped":
            key = "prompt_skipped"
        raw_p = g.get(key, "")
        if not raw_p and st == "skipped":
            raw_p = "This check was ignored via registry configuration."
        try:
            c["cursor_fix_prompt"] = raw_p.format(**ctx) if raw_p else ""
        except (KeyError, ValueError):
            c["cursor_fix_prompt"] = raw_p




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

    _enrich_checks_with_guidance(checks_out, project_name=project_name, repo_path=rp)

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
