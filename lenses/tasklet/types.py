from __future__ import annotations

from typing import Any, TypedDict


class TaskletRef(TypedDict, total=False):
    id: str
    version: int
    label: str


class TaskletRunRecord(TypedDict, total=False):
    id: str
    tasklet_id: str
    tasklet_version: int
    kind: str
    project_slug: str
    docs_health_session_id: str | None
    agent_runtime_session_id: str | None
    status: str
    created_at: str
    updated_at: str
    checkpoints: list[dict[str, Any]]
    sandbox_backend: str | None
    sandbox_handle: str | None
    metadata: dict[str, Any]


class CheckpointRecord(TypedDict, total=False):
    seq: int
    ts: str
    step: str
    note: str | None
