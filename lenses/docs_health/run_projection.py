"""Project docs-health session API view from TaskletRun + durable events (+ legacy session file)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lenses.docs_health import store
from lenses.docs_health.model_routing_preview import attach_model_routing_preview
from lenses.docs_health.remediation_scope import attach_remediation_scope
from lenses.docs_health.session_projection import session_public_view
from lenses.tasklet import store as tr_store
from lenses.tasklet.run_events import load_session_events, timeline_payloads_for_docs_health
from lenses.tasklet.state_machine import run_state_to_docs_session_status


def enrich_docs_health_session_view(workspace_root: Path | Any, project_slug: str, sess: dict[str, Any]) -> None:
    """Attach model routing preview + remediation scope for API consumers (mutates ``sess``)."""
    root = Path(workspace_root)
    attach_model_routing_preview(root, sess)
    attach_remediation_scope(root, project_slug, sess)


def merge_docs_health_session_view(
    workspace_root: Path | Any,
    project_slug: str,
    session_id: str,
) -> dict[str, Any] | None:
    """
    Load the session payload, overlay TaskletRun state, and prefer durable timeline events
    when ``events.jsonl`` exists for the run.
    """
    root = Path(workspace_root)
    sess = store.load_session(root, project_slug, session_id)
    if not sess:
        return None

    trid = str(sess.get("tasklet_run_id") or "").strip()
    if not trid:
        enrich_docs_health_session_view(root, project_slug, sess)
        return session_public_view(sess)

    run = tr_store.load_tasklet_run(root, trid)
    if not run:
        enrich_docs_health_session_view(root, project_slug, sess)
        return session_public_view(sess)

    raw_ev = load_session_events(root, trid)
    payloads = timeline_payloads_for_docs_health(raw_ev)
    if payloads:
        sess["events"] = payloads

    rs = str(run.get("state") or "")
    sr = str(run.get("stop_reason") or "")
    sess["run_state"] = rs
    sess["tasklet_run"] = {
        "id": run.get("id"),
        "state": rs,
        "stop_reason": run.get("stop_reason"),
        "event_seq": run.get("event_seq"),
        "checkpoints": run.get("checkpoints"),
        "sandbox": run.get("sandbox"),
        "sandbox_backend": run.get("sandbox_backend"),
    }
    sess["status"] = run_state_to_docs_session_status(rs, stop_reason=sr)

    enrich_docs_health_session_view(root, project_slug, sess)
    return session_public_view(sess)
