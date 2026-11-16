"""Structured stderr logging for virtual camera."""

from __future__ import annotations

import json
import sys
from typing import Any


def log_event(event: str, **fields: Any) -> None:
    payload: dict[str, Any] = {"module": "virtual-camera", "event": event}
    for k, v in fields.items():
        if v is not None:
            payload[k] = v
    print(json.dumps(payload, sort_keys=True, default=str), file=sys.stderr)
