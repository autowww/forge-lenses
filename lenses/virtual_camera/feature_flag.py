"""Feature flag for Virtual Camera Studio."""

from __future__ import annotations

import os


def experimental_virtual_camera_enabled() -> bool:
    """On when ``LENSES_EXPERIMENTAL_VIRTUAL_CAMERA`` is truthy."""
    raw = (os.environ.get("LENSES_EXPERIMENTAL_VIRTUAL_CAMERA") or "").strip().lower()
    return raw in ("1", "true", "yes", "on")
