"""Persist camera profiles under ``<workspace>/.lenses-local/virtual-camera-profiles.json``."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SETTINGS_FILENAME = "virtual-camera-profiles.json"
CURRENT_VERSION = 1

BLUR_LEVELS = frozenset({"off", "light", "medium", "strong"})

_DEFAULT: dict[str, Any] = {
    "version": CURRENT_VERSION,
    "profiles": [],
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def profiles_path(workspace_root: Path) -> Path:
    return workspace_root.resolve() / ".lenses-local" / SETTINGS_FILENAME


def load_raw(workspace_root: Path) -> dict[str, Any]:
    p = profiles_path(workspace_root)
    if not p.is_file():
        return json.loads(json.dumps(_DEFAULT))
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return json.loads(json.dumps(_DEFAULT))
    if not isinstance(data, dict):
        return json.loads(json.dumps(_DEFAULT))
    profiles = data.get("profiles")
    if not isinstance(profiles, list):
        profiles = []
    return {"version": CURRENT_VERSION, "profiles": [x for x in profiles if isinstance(x, dict)]}


def save_raw(workspace_root: Path, data: dict[str, Any]) -> None:
    p = profiles_path(workspace_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(p.parent, 0o700)
    except OSError:
        pass
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(p)
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass


def _normalize_source(src: Any) -> dict[str, str]:
    if not isinstance(src, dict):
        return {"stable_id": "", "device_path": "", "label": ""}
    return {
        "stable_id": str(src.get("stable_id") or "").strip(),
        "device_path": str(src.get("device_path") or "").strip(),
        "label": str(src.get("label") or "").strip(),
    }


def _normalize_virtual(virt: Any) -> dict[str, str]:
    if not isinstance(virt, dict):
        return {"device_path": "", "card_label": ""}
    return {
        "device_path": str(virt.get("device_path") or "").strip(),
        "card_label": str(virt.get("card_label") or "").strip(),
    }


def _normalize_resolution(res: Any) -> dict[str, int]:
    if not isinstance(res, dict):
        return {"width": 640, "height": 360}
    try:
        w = int(res.get("width") or 640)
        h = int(res.get("height") or 360)
    except (TypeError, ValueError):
        w, h = 640, 360
    return {"width": max(1, w), "height": max(1, h)}


def _normalize_crop(crop: Any) -> dict[str, int] | None:
    if crop is None:
        return None
    if not isinstance(crop, dict):
        return None
    try:
        return {
            "x": int(crop.get("x") or 0),
            "y": int(crop.get("y") or 0),
            "w": int(crop.get("w") or 0),
            "h": int(crop.get("h") or 0),
        }
    except (TypeError, ValueError):
        return None


def _normalize_recording(rec: Any) -> dict[str, Any]:
    if not isinstance(rec, dict):
        return {"enabled": False, "destination": ""}
    enabled = rec.get("enabled", False)
    if isinstance(enabled, str):
        enabled = enabled.strip().lower() in ("1", "true", "yes", "on")
    return {
        "enabled": bool(enabled),
        "destination": str(rec.get("destination") or "").strip(),
    }


def normalize_profile(raw: dict[str, Any], *, existing: dict[str, Any] | None = None) -> dict[str, Any]:
    prev = existing or {}
    pid = str(raw.get("id") or prev.get("id") or "").strip() or uuid.uuid4().hex
    blur = str(raw.get("blur_level") or prev.get("blur_level") or "off").strip().lower()
    if blur not in BLUR_LEVELS:
        blur = "off"
    try:
        fps = int(raw.get("fps") if "fps" in raw else prev.get("fps") or 15)
    except (TypeError, ValueError):
        fps = 15
    fps = max(1, min(120, fps))
    mirror_raw = raw.get("mirror") if "mirror" in raw else prev.get("mirror", False)
    if isinstance(mirror_raw, str):
        mirror = mirror_raw.strip().lower() in ("1", "true", "yes", "on")
    else:
        mirror = bool(mirror_raw)
    try:
        jpeg_quality = int(
            raw.get("jpeg_quality") if "jpeg_quality" in raw else prev.get("jpeg_quality") or 85
        )
    except (TypeError, ValueError):
        jpeg_quality = 85
    jpeg_quality = max(30, min(100, jpeg_quality))
    created = str(prev.get("created_at") or _now_iso())
    return {
        "id": pid,
        "name": str(raw.get("name") or prev.get("name") or "Camera profile").strip() or "Camera profile",
        "source": _normalize_source(raw.get("source") if "source" in raw else prev.get("source")),
        "virtual": _normalize_virtual(raw.get("virtual") if "virtual" in raw else prev.get("virtual")),
        "resolution": _normalize_resolution(
            raw.get("resolution") if "resolution" in raw else prev.get("resolution")
        ),
        "fps": fps,
        "input_format": str(
            raw.get("input_format") if "input_format" in raw else prev.get("input_format") or "MJPEG"
        ).strip()
        or "MJPEG",
        "output_format": str(
            raw.get("output_format") if "output_format" in raw else prev.get("output_format") or "YUYV"
        ).strip()
        or "YUYV",
        "crop": _normalize_crop(raw.get("crop") if "crop" in raw else prev.get("crop")),
        "mirror": mirror,
        "blur_level": blur,
        "jpeg_quality": jpeg_quality,
        "recording": _normalize_recording(
            raw.get("recording") if "recording" in raw else prev.get("recording")
        ),
        "created_at": created,
        "updated_at": _now_iso(),
    }


def list_profiles(workspace_root: Path) -> list[dict[str, Any]]:
    return list(load_raw(workspace_root).get("profiles") or [])


def get_profile(workspace_root: Path, profile_id: str) -> dict[str, Any] | None:
    pid = str(profile_id or "").strip()
    if not pid:
        return None
    for p in list_profiles(workspace_root):
        if str(p.get("id") or "") == pid:
            return dict(p)
    return None


def create_profile(workspace_root: Path, incoming: dict[str, Any]) -> dict[str, Any]:
    profile = normalize_profile(incoming)
    data = load_raw(workspace_root)
    profiles = list(data.get("profiles") or [])
    profiles.append(profile)
    data["profiles"] = profiles
    save_raw(workspace_root, data)
    return profile


def update_profile(workspace_root: Path, profile_id: str, incoming: dict[str, Any]) -> dict[str, Any] | None:
    pid = str(profile_id or "").strip()
    if not pid:
        return None
    data = load_raw(workspace_root)
    profiles = list(data.get("profiles") or [])
    for i, p in enumerate(profiles):
        if str(p.get("id") or "") != pid:
            continue
        merged = normalize_profile({**incoming, "id": pid}, existing=dict(p))
        profiles[i] = merged
        data["profiles"] = profiles
        save_raw(workspace_root, data)
        return merged
    return None


def delete_profile(workspace_root: Path, profile_id: str) -> bool:
    pid = str(profile_id or "").strip()
    if not pid:
        return False
    data = load_raw(workspace_root)
    profiles = list(data.get("profiles") or [])
    kept = [p for p in profiles if str(p.get("id") or "") != pid]
    if len(kept) == len(profiles):
        return False
    data["profiles"] = kept
    save_raw(workspace_root, data)
    return True


def duplicate_profile(workspace_root: Path, profile_id: str) -> dict[str, Any] | None:
    src = get_profile(workspace_root, profile_id)
    if not src:
        return None
    copy = dict(src)
    copy.pop("id", None)
    copy["name"] = f"{src.get('name', 'Profile')} (copy)"
    return create_profile(workspace_root, copy)
