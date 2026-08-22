from __future__ import annotations

from typing import Any

# Built-in tasklets (versioned). Executor names map to Docs Health / future dispatch tables.
_BUILTIN: dict[tuple[str, int], dict[str, Any]] = {
    ("docs_health_remediation", 1): {
        "id": "docs_health_remediation",
        "version": 1,
        "kind": "docs_health_remediation",
        "label": "Docs Health — cluster remediation",
        "executor": "docs_health_session_step",
        "schema_version": 1,
        "sandbox": "optional",
        "description": "Interactive markdown remediation for a documentation cluster (enrich, draft, review, apply, verify).",
    },
}


def resolve_tasklet(tasklet_id: str, version: int) -> dict[str, Any] | None:
    return _BUILTIN.get((str(tasklet_id or "").strip(), int(version)))


def describe_tasklet(tasklet_id: str, version: int) -> dict[str, Any]:
    spec = resolve_tasklet(tasklet_id, version)
    if not spec:
        return {"id": tasklet_id, "version": version, "label": "Unknown tasklet", "unknown": True}
    return dict(spec)


def list_builtin_tasklet_definitions() -> list[dict[str, Any]]:
    """Stable list for Studio / API (no filesystem reads)."""
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for (tid, ver), row in sorted(_BUILTIN.items(), key=lambda x: (x[0][0], x[0][1])):
        if (tid, ver) in seen:
            continue
        seen.add((tid, ver))
        out.append(dict(row))
    return out
