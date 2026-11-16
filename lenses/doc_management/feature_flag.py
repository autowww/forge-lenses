"""Feature gate for Doc Management (on by default; set LENSES_DOC_MANAGEMENT=0 to disable)."""

from __future__ import annotations

import os


def doc_management_enabled() -> bool:
    v = (os.environ.get("LENSES_DOC_MANAGEMENT") or "").strip().lower()
    if v in ("0", "false", "no", "off"):
        return False
    return True
