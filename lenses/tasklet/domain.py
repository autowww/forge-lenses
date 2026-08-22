"""Generic runtime domain objects for Tasklet execution (workload-agnostic)."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

# --- Tasklet definition (versioned workload) ---------------------------------

class TaskletDefinition(TypedDict, total=False):
    """Immutable description of a workload type (compare to a semver’d spec)."""

    id: str
    version: int
    label: str
    kind: str
    executor: str
    schema_version: int


# --- Run record ---------------------------------------------------------------

RunState = Literal[
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
]

StopReason = Literal["cancelled", "operator", "error", "none"]


class RunCheckpoint(TypedDict, total=False):
    """Coarse resumable marker (step name + optional run state snapshot)."""

    seq: int
    ts: str
    step: str
    run_state: str | None
    note: str | None


class RunArtifact(TypedDict, total=False):
    """Reference to a durable artifact (patch file, bundle, verification output)."""

    id: str
    kind: str
    path: str | None
    uri: str | None
    bytes: int | None
    created_at: str
    meta: dict[str, Any]


class SessionEvent(TypedDict, total=False):
    """
    Append-only timeline event for a TaskletRun (durable log + UI reconstruction).

    ``payload`` holds domain-specific shape (e.g. docs-health timeline row).
    """

    seq: int
    ts: str
    kind: str
    payload: dict[str, Any]


class TaskletRun(TypedDict, total=False):
    """Persisted TaskletRun aggregate (see ``tasklet/store.py``)."""

    id: str
    tasklet_id: str
    tasklet_version: int
    kind: str
    project_slug: str
    state: RunState
    stop_reason: StopReason | str | None
    docs_health_session_id: str | None
    agent_runtime_session_id: str | None
    created_at: str
    updated_at: str
    checkpoints: list[RunCheckpoint]
    artifacts: list[RunArtifact]
    event_seq: int
    sandbox_backend: str | None
    sandbox_handle: str | None
    sandbox: dict[str, Any] | None
    metadata: dict[str, Any]
    last_error: str | None
