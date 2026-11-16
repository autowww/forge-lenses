"""Sync docs-health session dict with TaskletRun state machine + durable events."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lenses.tasklet import store as tr_store
from lenses.tasklet.run_events import append_session_events
from lenses.tasklet.state_machine import (
    docs_session_status_to_run_state,
    is_terminal,
    transition_allowed,
    try_apply_state_transition,
)


def tasklet_allows_new_steps(workspace_root: Path | Any, sess: dict[str, Any]) -> bool:
    """False when TaskletRun is terminal (stopped / completed / failed)."""
    trid = str(sess.get("tasklet_run_id") or "").strip()
    if not trid:
        return True
    rec = tr_store.load_tasklet_run(Path(workspace_root), trid)
    if not rec:
        return True
    return not is_terminal(str(rec.get("state") or ""))


def mark_verify_phase_started(workspace_root: Path | Any, sess: dict[str, Any]) -> None:
    trid = str(sess.get("tasklet_run_id") or "").strip()
    if not trid:
        return
    try_apply_state_transition(Path(workspace_root), trid, "verifying")


def sync_docs_health_timeline(
    workspace_root: Path | Any,
    project_slug: str,
    sess: dict[str, Any],
    *,
    step: str,
    timeline_slice: list[dict[str, Any]],
    explicit_run_state: str | None = None,
) -> None:
    """
    After ``store.write_session``, update TaskletRun state and append durable timeline rows.

    ``timeline_slice`` should be new events appended this step (same shape as session ``events``).
    """
    root = Path(workspace_root)
    trid = str(sess.get("tasklet_run_id") or "").strip()
    if not trid:
        return

    rec = tr_store.load_tasklet_run(root, trid)
    if not rec:
        return
    if is_terminal(str(rec.get("state") or "")):
        return

    if explicit_run_state:
        target = explicit_run_state
    else:
        target = docs_session_status_to_run_state(str(sess.get("status") or ""))

    ok, _err = try_apply_state_transition(root, trid, target)
    if not ok:
        return

    rec2 = tr_store.load_tasklet_run(root, trid)
    if not rec2:
        return
    base = int(rec2.get("event_seq") or 0)
    to_append = [x for x in timeline_slice if isinstance(x, dict)]
    next_seq = append_session_events(root, trid, base_seq=base, events=to_append)
    tr_store.update_tasklet_run(root, trid, event_seq=next_seq)

    tr_store.append_checkpoint(
        root,
        trid,
        step=step,
        note=None,
        run_state=str(rec2.get("state") or target),
    )


def bootstrap_docs_health_run(workspace_root: Path | Any, run_id: str) -> None:
    """created → preparing → running (initial remediation session)."""
    root = Path(workspace_root)
    try_apply_state_transition(root, run_id, "preparing")
    try_apply_state_transition(root, run_id, "running")


def resume_docs_health_run(workspace_root: Path | Any, run_id: str) -> tuple[bool, str | None]:
    """
    ``stopped`` → ``running`` so a new Docker sandbox can continue from on-disk session + checkpoints.

    Used after a hard stop when the operator chooses to continue the same remediation session.
    """
    root = Path(workspace_root)
    rec = tr_store.load_tasklet_run(root, run_id)
    if not rec:
        return False, "run_not_found"
    if str(rec.get("state") or "") != "stopped":
        return False, "not_stopped"
    ok, err = try_apply_state_transition(root, run_id, "running")
    return (ok, err)


def cancel_docs_health_run(workspace_root: Path | Any, run_id: str) -> None:
    """Non-terminal → stopping → stopped(cancelled)."""
    root = Path(workspace_root)
    rec = tr_store.load_tasklet_run(root, run_id)
    if not rec:
        return
    st = str(rec.get("state") or "")
    if is_terminal(st):
        return
    if transition_allowed(st, "stopping"):
        try_apply_state_transition(root, run_id, "stopping")
    try_apply_state_transition(root, run_id, "stopped", stop_reason="cancelled")


def complete_docs_health_run(workspace_root: Path | Any, run_id: str) -> None:
    try_apply_state_transition(Path(workspace_root), run_id, "completed")


def fail_docs_health_run(workspace_root: Path | Any, run_id: str, message: str) -> None:
    try_apply_state_transition(Path(workspace_root), run_id, "failed", last_error=message[:4000])


def seed_docs_health_session_timeline(
    workspace_root: Path | Any,
    run_id: str,
    events: list[dict[str, Any]],
) -> None:
    """Persist initial session timeline into JSONL so GET can reconstruct from run events alone."""
    root = Path(workspace_root)
    to_seed = [e for e in events if isinstance(e, dict)]
    if not to_seed:
        return
    next_seq = append_session_events(root, run_id, base_seq=0, events=to_seed)
    tr_store.update_tasklet_run(root, run_id, event_seq=next_seq)
