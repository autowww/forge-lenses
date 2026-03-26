"""Debounced headless capture of board editor → PNG under .lenses-local/sticker-board-previews/."""

from __future__ import annotations

import os
import threading
import urllib.parse
from pathlib import Path

from lenses.sticker_board import board_preview_path

# One pending timer per board id (cancel/replace on rapid saves).
_timers: dict[str, threading.Timer] = {}
_lock = threading.Lock()
_DEBOUNCE_SEC = 20.0

# Slightly smaller than doc previews; enough for freeform / kanban frame.
_THUMB_SIZE = (900, 560)
_VIRTUAL_TIME_MS = 14_000


def board_previews_enabled() -> bool:
    v = (os.environ.get("LENSES_BOARD_PREVIEWS") or "1").strip().lower()
    return v not in ("0", "false", "no", "off")


def schedule_board_preview_capture(
    *,
    public_base_url: str,
    workspace_root: Path,
    board_id: str,
) -> None:
    """After sticker board save: debounce then screenshot ``/board/<id>?thumb=1``."""
    if not board_previews_enabled():
        return

    def run_capture() -> None:
        with _lock:
            _timers.pop(board_id, None)
        dest = board_preview_path(workspace_root, board_id)
        url = (
            public_base_url.rstrip("/")
            + "/board/"
            + urllib.parse.quote(board_id, safe="")
            + "?thumb=1"
        )
        try:
            from lenses.html2image_capture import capture_url_to_png
        except ImportError:
            return
        capture_url_to_png(
            url,
            dest,
            size=_THUMB_SIZE,
            virtual_time_budget_ms=_VIRTUAL_TIME_MS,
        )

    def fire() -> None:
        try:
            run_capture()
        except Exception:
            pass

    with _lock:
        old = _timers.pop(board_id, None)
        if old is not None:
            old.cancel()
        t = threading.Timer(_DEBOUNCE_SEC, fire)
        t.daemon = True
        _timers[board_id] = t
        t.start()
