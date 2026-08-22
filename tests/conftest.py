"""Pytest hooks: extend sys.path for script-local test helpers."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Docs Health: default to inline steps so the suite does not require a Docker image/CLI.
os.environ.setdefault("LENSES_DOCS_HEALTH_STEP_BACKEND", "inline")

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = _ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
