"""CLI entry for isolated Docs Health steps (subprocess / Docker worker)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from lenses.docs_health import store


def _write_container_heartbeat() -> None:
    root = os.environ.get("LENSES_CHECKPOINT_ROOT", "").strip()
    if not root:
        return
    p = Path(root) / "container_heartbeat.json"
    try:
        p.write_text(
            json.dumps({"ts": store.now_iso(), "pid": os.getpid()}, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        os.chmod(p, 0o600)
    except OSError:
        pass
from lenses.docs_health.run_sync import tasklet_allows_new_steps
from lenses.docs_health.session_steps import execute_docs_health_session_step


def _bundle_from_env() -> dict[str, Any]:
    return {
        "can_read_project": True,
        "can_write_project": os.environ.get("LENSES_STEP_BUNDLE_WRITE", "").strip() == "1",
        "effective_readonly": os.environ.get("LENSES_STEP_EFFECTIVE_READONLY", "").strip() == "1",
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Run one Docs Health session_step in isolation.")
    p.add_argument("--workspace-root", required=True)
    p.add_argument("--project-slug", required=True)
    p.add_argument("--session-id", required=True)
    p.add_argument("--step", required=True)
    p.add_argument("--repo-root", required=True)
    args = p.parse_args(argv)

    ws = Path(args.workspace_root)
    sid = str(args.session_id).strip()
    slug = str(args.project_slug).strip()
    child = Path(args.repo_root).resolve()
    sess = store.load_session(ws, slug, sid)
    if not sess:
        print(json.dumps({"ok": False, "error": "session_not_found", "http_status": 404}))
        return 2
    _write_container_heartbeat()
    st = str(sess.get("status") or "").lower()
    if st in ("cancelled", "completed", "failed") or not tasklet_allows_new_steps(ws, sess):
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "session_not_active",
                    "http_status": 409,
                    "detail": st if st in ("cancelled", "completed", "failed") else "tasklet_terminal",
                }
            )
        )
        return 3

    code, body = execute_docs_health_session_step(
        ws,
        child,
        slug,
        sess,
        str(args.step).strip().lower(),
        _bundle_from_env(),
    )
    print(json.dumps({"ok": code >= 200 and code < 300, "http_status": code, "body": body}, default=str))
    return 0 if code < 500 else 1


if __name__ == "__main__":
    raise SystemExit(main())
