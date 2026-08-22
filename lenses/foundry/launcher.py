"""Subprocess launcher for forge-dark-factory CLI."""

from __future__ import annotations

import os
import sys
import threading
from pathlib import Path
from typing import Any, Callable

from lenses.foundry.payload import normalize_run_dir


def resolve_dark_factory_root(lenses_repo_root: Path) -> Path | None:
    env = (os.environ.get("FOUNDRY_DARK_FACTORY_ROOT") or "").strip()
    if env:
        p = Path(env).expanduser().resolve()
        return p if (p / "src" / "forge_dark_factory").is_dir() else None
    sibling = lenses_repo_root.parent / "forge-dark-factory"
    if (sibling / "src" / "forge_dark_factory").is_dir():
        return sibling.resolve()
    return None


def resolve_lcdl_src(dark_factory_root: Path) -> Path | None:
    env = (os.environ.get("FOUNDRY_LCDL_SRC") or "").strip()
    if env:
        p = Path(env).expanduser().resolve()
        return p if p.is_dir() else None
    sibling = dark_factory_root.parent / "forge-lcdl" / "src"
    return sibling.resolve() if sibling.is_dir() else None


def build_df_env(dark_factory_root: Path) -> dict[str, str]:
    env = dict(os.environ)
    parts: list[str] = [str(dark_factory_root / "src")]
    lcdl = resolve_lcdl_src(dark_factory_root)
    if lcdl:
        parts.append(str(lcdl))
    prev = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = os.pathsep.join(parts + ([prev] if prev else []))
    return env


def launch_run_async(
    *,
    lenses_repo_root: Path,
    goal: str,
    target: Path,
    out_parent: Path,
    level: str,
    worker: str,
    fixture: Path | None,
    allowed_files: tuple[str, ...] | None = None,
    verification_argv: tuple[str, ...] | None = None,
    workspace_root: Path | None = None,
    run_id: str = "",
    on_complete: Callable[[dict[str, Any]], None],
    on_error: Callable[[str], None],
) -> None:
    def _worker() -> None:
        df_root = resolve_dark_factory_root(lenses_repo_root)
        if df_root is None:
            on_error("forge-dark-factory checkout not found (set FOUNDRY_DARK_FACTORY_ROOT)")
            return
        out_parent.mkdir(parents=True, exist_ok=True)
        df_src = str(df_root / "src")
        if df_src not in sys.path:
            sys.path.insert(0, df_src)
        lcdl = resolve_lcdl_src(df_root)
        if lcdl and str(lcdl) not in sys.path:
            sys.path.insert(0, str(lcdl))
        try:
            from forge_dark_factory.driver import DriverConfig, run as df_run
        except ImportError as exc:
            on_error(f"forge_dark_factory import failed: {exc}")
            return

        def on_phase(phase: Any) -> None:
            if workspace_root is None or not run_id:
                return
            from lenses.foundry.activity import sync_phase_progress

            sync_phase_progress(workspace_root, run_id, phase)

        config = DriverConfig(
            goal=goal,
            target=target,
            out_dir=out_parent,
            worker_backend=worker,
            fixture_path=fixture,
            level=level,
            keep_worktree=True,
            allowed_files=allowed_files,
            verification_argv=verification_argv,
            on_phase=on_phase if workspace_root and run_id else None,
        )
        try:
            result = df_run(config)
        except Exception as exc:
            on_error(str(exc)[:2000])
            return
        run_dir = out_parent / result.run_id if (out_parent / result.run_id).is_dir() else None
        if run_dir is None:
            run_dirs = sorted(out_parent.glob("run-*"), key=lambda p: p.stat().st_mtime, reverse=True)
            run_dir = run_dirs[0] if run_dirs else None
        if run_dir is None:
            on_error("no run directory produced")
            return
        normalized = normalize_run_dir(run_dir)
        normalized["exit_code"] = 0 if result.final_status == "pass" else 1
        on_complete(normalized)

    threading.Thread(target=_worker, daemon=True).start()
