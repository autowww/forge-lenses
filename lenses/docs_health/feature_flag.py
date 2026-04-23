"""Feature gate for Docs Health (on by default; set LENSES_DOCS_HEALTH=0 to disable)."""

from __future__ import annotations

import os


def docs_health_enabled() -> bool:
    v = (os.environ.get("LENSES_DOCS_HEALTH") or "").strip().lower()
    if v in ("0", "false", "no", "off"):
        return False
    return True
