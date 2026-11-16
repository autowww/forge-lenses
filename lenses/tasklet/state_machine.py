"""TaskletRun lifecycle: explicit states and allowed transitions."""

from __future__ import annotations

from typing import Any

RUN_STATES: frozenset[str] = frozenset(
    {
        "created",
        "preparing",
        "running",
        "awaiting_input",
        "awaiting_approval",
        "paused",
        "stopping",
        "stopped",
        "verifying",
        "completed",
        "failed",
    }
)

_TERMINAL: frozenset[str] = frozenset({"stopped", "completed", "failed"})

# Allowed directed transitions (excluding self no-ops handled by caller).
_ALLOWED: dict[str, frozenset[str]] = {
    "created": frozenset({"preparing", "failed", "stopping"}),
    "preparing": frozenset({"running", "failed", "stopping"}),
    "running": frozenset(
        {
            "awaiting_input",
            "awaiting_approval",
            "verifying",
            "paused",
            "completed",
            "failed",
            "stopping",
        }
    ),
    "awaiting_input": frozenset({"running", "paused", "failed", "stopping"}),
    "awaiting_approval": frozenset({"running", "paused", "failed", "stopping", "verifying"}),
    "paused": frozenset({"running", "failed", "stopping"}),
    "verifying": frozenset({"completed", "failed", "stopping"}),
    "stopping": frozenset({"stopped"}),
    "stopped": frozenset({"running"}),
    "completed": frozenset(),
    "failed": frozenset(),
}


def is_terminal(state: str | None) -> bool:
    return str(state or "").strip().lower() in _TERMINAL


def transition_allowed(from_state: str | None, to_state: str | None) -> bool:
    a = str(from_state or "").strip().lower()
    b = str(to_state or "").strip().lower()
    if not b or b not in RUN_STATES:
        return False
    if a == b:
        return True
    # Operator resume: new Docker sandbox continues from persisted checkpoints.
    if a == "stopped" and b == "running":
        return True
    if is_terminal(a):
        return False
    return b in _ALLOWED.get(a, frozenset())


def normalize_run_record(rec: dict[str, Any]) -> dict[str, Any]:
    """Migrate legacy ``status`` on tasklet JSON to ``state``."""
    if str(rec.get("state") or "").strip():
        return rec
    legacy = str(rec.get("status") or "").strip().lower()
    if legacy == "cancelled":
        rec["state"] = "stopped"
        rec["stop_reason"] = "cancelled"
    elif legacy == "completed":
        rec["state"] = "completed"
    else:
        rec["state"] = "running" if legacy in ("", "running", "live") else "running"
    return rec


def docs_session_status_to_run_state(status: str | None, *, phase_verify: bool = False) -> str:
    """Map docs-health session ``status`` string to RunState."""
    s = str(status or "").strip().lower()
    if phase_verify:
        return "verifying"
    if s in ("awaiting_input",):
        return "awaiting_input"
    if s in ("awaiting_approval",):
        return "awaiting_approval"
    if s in ("completed",):
        return "completed"
    if s in ("cancelled",):
        return "stopped"
    if s in ("failed",):
        return "failed"
    if s in ("paused",):
        return "paused"
    return "running"


def try_apply_state_transition(
    workspace_root: Any,
    run_id: str,
    new_state: str,
    *,
    stop_reason: str | None = None,
    last_error: str | None = None,
) -> tuple[bool, str | None]:
    """
    Apply a transition to persisted TaskletRun. Returns ``(ok, error_message)``.
    """
    from pathlib import Path

    from lenses.tasklet import store as tr_store

    root = Path(workspace_root)
    rec = tr_store.load_tasklet_run(root, run_id)
    if not rec:
        return False, "run_not_found"
    rec = normalize_run_record(rec)
    old = str(rec.get("state") or "created")
    if not transition_allowed(old, new_state):
        return False, f"invalid_transition:{old}->{new_state}"
    new_s = str(new_state).strip().lower()
    rec["state"] = new_s
    # Resume: operator continues a stopped run — clear terminal stop metadata.
    if new_s == "running" and old == "stopped":
        rec["stop_reason"] = None
        rec["last_error"] = None
        rec.pop("status", None)
    elif stop_reason is not None:
        rec["stop_reason"] = stop_reason
    if last_error is not None:
        rec["last_error"] = last_error
    # Legacy readers (pre–Sprint 1): mirror terminal state on ``status`` when present.
    if str(new_state).strip().lower() in ("stopped", "completed", "failed"):
        rec["status"] = {"stopped": "cancelled", "completed": "completed", "failed": "failed"}.get(
            str(new_state).strip().lower(), "cancelled"
        )
    tr_store.write_tasklet_run(root, rec)
    return True, None


def run_state_to_docs_session_status(state: str | None, *, stop_reason: str | None = None) -> str:
    """Project RunState to legacy docs-health session status for Studio compatibility."""
    r = str(state or "").strip().lower()
    if r == "stopped":
        if str(stop_reason or "").strip().lower() == "cancelled":
            return "cancelled"
        return "failed"
    if r == "verifying":
        return "running"
    if r == "failed":
        return "failed"
    if r in ("created", "preparing", "running", "stopping"):
        return "running"
    if r == "awaiting_input":
        return "awaiting_input"
    if r == "awaiting_approval":
        return "awaiting_approval"
    if r == "paused":
        return "paused"
    if r == "completed":
        return "completed"
    return "running"
