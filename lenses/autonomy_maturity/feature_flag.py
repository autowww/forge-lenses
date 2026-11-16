"""Feature flag for the autonomy maturity assessment panel."""

from __future__ import annotations

import os


def experimental_autonomy_maturity_enabled() -> bool:
    """Off by default. Set ``LENSES_EXPERIMENTAL_AUTONOMY_MATURITY=1`` to enable."""
    raw = (os.environ.get("LENSES_EXPERIMENTAL_AUTONOMY_MATURITY") or "").strip().lower()
    return raw in ("1", "true", "yes", "on")
