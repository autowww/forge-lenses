"""Map GStreamer stderr to stable error codes for the Studio UI."""

from __future__ import annotations

from typing import Any

ERROR_CODES = frozenset(
    {
        "CAMERA_BUSY",
        "FORMAT_NEGOTIATION_FAILED",
        "DEVICE_MISSING",
        "PIPELINE_FAILED",
        "UNKNOWN",
    }
)


def classify_gst_stderr(text: str) -> dict[str, Any]:
    raw = (text or "").strip()
    lower = raw.lower()
    code = "UNKNOWN"
    message = raw[:500] if raw else "Pipeline failed."

    if "device or resource busy" in lower or "resource busy" in lower:
        code = "CAMERA_BUSY"
        message = "The physical camera is already being used by another application."
    elif "not-negotiated" in lower or "could not negotiate" in lower:
        code = "FORMAT_NEGOTIATION_FAILED"
        message = "The selected camera resolution, frame rate, or format is unsupported."
    elif "no such file or directory" in lower:
        code = "DEVICE_MISSING"
        message = "The selected camera is no longer connected."
    elif raw:
        code = "PIPELINE_FAILED"
        message = raw.splitlines()[-1][:300]

    return {
        "code": code,
        "message": message,
        "raw": raw[:2048],
    }


def classify_busy_preflight() -> dict[str, Any]:
    return {
        "code": "CAMERA_BUSY",
        "message": "The physical camera is already being used by another application.",
        "raw": "",
    }
