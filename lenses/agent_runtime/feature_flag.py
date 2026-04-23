"""Feature gate for agent runtime HTTP (default on)."""

from __future__ import annotations

import os


def agent_runtime_enabled() -> bool:
    v = (os.environ.get("LENSES_AGENT_RUNTIME") or "1").strip().lower()
    return v not in ("0", "false", "no", "off")
