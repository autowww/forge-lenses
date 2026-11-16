"""Post-apply verification bundle (bounded; optional external tools)."""

from __future__ import annotations

import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any

from lenses.docs_health.scanner import LINK_RE


def _resolve_md_link(repo: Path, from_file: Path, target: str) -> bool:
    t = (target or "").strip()
    if not t or t.startswith(("#", "http://", "https://", "mailto:")):
        return True
    t = t.split("#", 1)[0].strip()
    if not t:
        return True
    dest = (from_file.parent / t).resolve()
    try:
        dest.relative_to(repo.resolve())
    except ValueError:
        return False
    return dest.is_file()


def check_markdown_links_for_paths(repo_root: Path, rel_paths: list[str]) -> dict[str, Any]:
    """Validate relative markdown links for listed repo-relative paths."""
    repo = repo_root.resolve()
    broken: list[dict[str, str]] = []
    checked = 0
    for rel in rel_paths:
        rel = str(rel or "").strip().replace("\\", "/")
        if ".." in rel or rel.startswith("/"):
            continue
        if not rel.lower().endswith(".md"):
            continue
        p = (repo / rel).resolve()
        try:
            p.relative_to(repo)
        except ValueError:
            continue
        if not p.is_file():
            continue
        checked += 1
        text = p.read_text(encoding="utf-8", errors="replace")
        for m in LINK_RE.finditer(text):
            tgt = m.group(1).strip()
            if not _resolve_md_link(repo, p, tgt):
                broken.append({"from": rel, "target": tgt[:500]})
    return {
        "ok": len(broken) == 0,
        "checked_files": checked,
        "broken_links": broken[:50],
        "broken_count": len(broken),
    }


def maybe_run_markdownlint(rel_paths: list[str], repo_root: Path) -> dict[str, Any]:
    exe = shutil.which("markdownlint")
    if not exe or not rel_paths:
        return {"skipped": True, "reason": "markdownlint_not_on_path_or_no_paths"}
    args = [exe] + [str(repo_root / p) for p in rel_paths[:30] if p and ".." not in p]
    if len(args) < 2:
        return {"skipped": True, "reason": "no_valid_paths"}
    try:
        proc = subprocess.run(
            args,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        return {
            "skipped": False,
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": (proc.stdout or "")[-8000:],
            "stderr": (proc.stderr or "")[-8000:],
        }
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"skipped": False, "ok": False, "error": str(e)}


def run_post_apply_bundle(
    repo_root: Path,
    *,
    applied_rel_paths: list[str],
) -> dict[str, Any]:
    """Run link validation + optional markdownlint after a patch apply."""
    uniq = sorted({str(p).replace("\\", "/") for p in applied_rel_paths if str(p).strip()})
    links = check_markdown_links_for_paths(repo_root, uniq)
    lint = maybe_run_markdownlint(uniq, repo_root)
    ok = bool(links.get("ok")) and (lint.get("skipped") or lint.get("ok"))
    return {
        "ok": ok,
        "steps": {
            "markdown_links": links,
            "markdownlint": lint,
        },
    }


def _parse_cmd(cmd: Any) -> list[str] | None:
    if isinstance(cmd, list) and cmd:
        return [str(x) for x in cmd if str(x).strip()]
    if isinstance(cmd, str) and cmd.strip():
        return shlex.split(cmd.strip())
    return None


def run_contract_verification(repo_root: Path, contract: dict[str, Any] | None) -> dict[str, Any]:
    """
    Optional checklist-driven commands from ``forge/docs-contract.yaml``:

    .. code-block:: yaml

        post_apply_verification:
          commands:
            - name: handbook_build
              cmd: "python3 generator/build-handbook.py --all"
              cwd: "."
              timeout_sec: 300
    """
    c = contract if isinstance(contract, dict) else {}
    pav = c.get("post_apply_verification")
    if not isinstance(pav, dict):
        return {"skipped": True, "reason": "not_configured", "results": []}
    cmds = pav.get("commands")
    if not isinstance(cmds, list) or not cmds:
        return {"skipped": True, "reason": "no_commands", "results": []}
    repo = repo_root.resolve()
    results: list[dict[str, Any]] = []
    all_ok = True
    for spec in cmds:
        if not isinstance(spec, dict):
            continue
        name = str(spec.get("name") or "command").strip() or "command"
        argv = _parse_cmd(spec.get("cmd"))
        if not argv:
            results.append({"name": name, "skipped": True, "reason": "invalid_cmd"})
            continue
        cwd_rel = str(spec.get("cwd") or ".").strip() or "."
        if ".." in cwd_rel or cwd_rel.startswith("/"):
            results.append({"name": name, "ok": False, "error": "invalid_cwd"})
            all_ok = False
            continue
        cwd = (repo / cwd_rel).resolve()
        try:
            cwd.relative_to(repo)
        except ValueError:
            results.append({"name": name, "ok": False, "error": "cwd_escape"})
            all_ok = False
            continue
        timeout = int(spec.get("timeout_sec") or 300)
        timeout = max(5, min(timeout, 3600))
        try:
            proc = subprocess.run(
                argv,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            row = {
                "name": name,
                "ok": proc.returncode == 0,
                "returncode": proc.returncode,
                "stdout": (proc.stdout or "")[-6000:],
                "stderr": (proc.stderr or "")[-6000:],
            }
            results.append(row)
            all_ok = all_ok and bool(row["ok"])
        except (OSError, subprocess.TimeoutExpired) as e:
            results.append({"name": name, "ok": False, "error": str(e)})
            all_ok = False
    return {"skipped": False, "ok": all_ok, "results": results}


def run_post_apply_verification(
    repo_root: Path,
    *,
    applied_rel_paths: list[str],
    contract: dict[str, Any] | None,
) -> dict[str, Any]:
    """Links + markdownlint on touched files, then optional contract commands (build/tests)."""
    base = run_post_apply_bundle(repo_root, applied_rel_paths=applied_rel_paths)
    contract_part = run_contract_verification(repo_root, contract)
    contract_ok = bool(contract_part.get("skipped")) or bool(contract_part.get("ok"))
    ok = bool(base.get("ok")) and contract_ok
    return {
        "ok": ok,
        "steps": {
            **base.get("steps", {}),
            "contract_commands": contract_part,
        },
    }
