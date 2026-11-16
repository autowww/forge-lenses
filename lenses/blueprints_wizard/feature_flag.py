"""Server-side feature flag for the experimental Blueprints Wizard."""

from __future__ import annotations

import os


def experimental_blueprints_wizard_enabled() -> bool:
    """Wizard APIs are on by default. Set ``LENSES_EXPERIMENTAL_BLUEPRINTS_WIZARD=0`` (or ``false`` / ``no`` / ``off``) to disable."""
    raw = (os.environ.get("LENSES_EXPERIMENTAL_BLUEPRINTS_WIZARD") or "").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    if not raw:
        return True
    return raw in ("1", "true", "yes", "on")
