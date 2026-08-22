"""VDI / Azure Teams readiness helpers for Virtual Camera Studio."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lenses.virtual_camera.discovery import discover_cameras, formats_for_device_path
from lenses.virtual_camera.loopback import bootstrap_status
from lenses.virtual_camera.pipeline import (
    list_ui_output_formats,
    normalize_output_format,
    vdi_friendly_formats,
)
from lenses.virtual_camera import profiles_store
from lenses.virtual_camera.runtime import get_profile_runtime

RDP_PROPERTY_LINES = [
    "camerastoredirect:s:*",
    "redirected video capture encoding quality:i:2",
    "encode redirected video capture:i:1",
    "audiocapturemode:i:1",
    "audiomode:i:0",
]

TEAMS_ON_AVD_URL = "https://learn.microsoft.com/en-us/azure/virtual-desktop/teams-on-avd"
RDP_PROPERTIES_URL = "https://learn.microsoft.com/en-us/azure/virtual-desktop/rdp-properties"


def _virtual_device_entry(device_path: str) -> dict[str, Any] | None:
    path = str(device_path or "").strip()
    if not path:
        return None
    disc = discover_cameras()
    for cam in disc.get("virtual") or []:
        if str(cam.get("device_path") or "") == path:
            return cam
    bootstrap = bootstrap_status()
    for dev in bootstrap.get("loopback_devices") or []:
        if str(dev.get("device_path") or "") == path:
            return dev
    return {"device_path": path}


def vdi_readiness_payload(workspace_root: Path) -> dict[str, Any]:
    bootstrap = bootstrap_status()
    profiles = profiles_store.list_profiles(workspace_root)
    running = []
    for p in profiles:
        pid = str(p.get("id") or "")
        rt = get_profile_runtime(workspace_root, pid)
        state = str(rt.get("state") or "stopped").lower()
        if state == "running":
            virtual = p.get("virtual") or {}
            sink = str(virtual.get("device_path") or "")
            vf = formats_for_device_path(sink) if sink else []
            running.append(
                {
                    "id": pid,
                    "name": p.get("name"),
                    "output_format": normalize_output_format(str(p.get("output_format") or "YUYV")),
                    "resolution": p.get("resolution"),
                    "fps": p.get("fps"),
                    "virtual_device_path": sink,
                    "virtual_output_formats": list_ui_output_formats(vf),
                }
            )

    virtual_devices: list[dict[str, Any]] = []
    disc = discover_cameras()
    seen: set[str] = set()
    for cam in disc.get("virtual") or []:
        path = str(cam.get("device_path") or "").strip()
        if not path or path in seen:
            continue
        seen.add(path)
        vf = cam.get("formats") or formats_for_device_path(path)
        virtual_devices.append(
            {
                "device_path": path,
                "label": cam.get("label") or cam.get("card_label"),
                "formats": vf,
                "output_format_options": list_ui_output_formats(vf),
                "vdi_friendly": vdi_friendly_formats(vf),
            }
        )

    for dev in bootstrap.get("loopback_devices") or []:
        path = str(dev.get("device_path") or "").strip()
        if not path or path in seen:
            continue
        seen.add(path)
        vf = formats_for_device_path(path)
        virtual_devices.append(
            {
                "device_path": path,
                "label": dev.get("card_label"),
                "formats": vf,
                "output_format_options": list_ui_output_formats(vf),
                "vdi_friendly": vdi_friendly_formats(vf),
            }
        )

    recommended_output = "MJPEG"
    if virtual_devices:
        opts = virtual_devices[0].get("output_format_options") or []
        if "MJPEG" in opts:
            recommended_output = "MJPEG"
        elif "NV12" in opts:
            recommended_output = "NV12"
        else:
            recommended_output = str(opts[0] if opts else "YUYV")

    return {
        "ok": True,
        "bootstrap": bootstrap,
        "linux_primary_note": (
            "Media Foundation virtual cameras are Windows-only. On Linux, use v4l2loopback "
            "with MJPEG or NV12 output for Azure VDI RDP camera redirect."
        ),
        "teams_optimization_note": (
            "Teams media optimization on Azure Virtual Desktop requires a supported client "
            "(Windows App on Windows/Mac, or partner Linux thin clients). Generic Ubuntu "
            "Remote Desktop usually uses RDP camera redirect — prefer MJPEG output and "
            "640×360 @ 15 fps, or VDI ultra-low (320×160) / minimal (160×120) when Teams "
            "is not VDI-optimized."
        ),
        "recommended_preset_id": "avd_teams",
        "recommended_output_format": recommended_output,
        "recommended_resolution": {"width": 640, "height": 360},
        "recommended_fps": 15,
        "rdp_property_lines": RDP_PROPERTY_LINES,
        "links": {
            "teams_on_avd": TEAMS_ON_AVD_URL,
            "rdp_properties": RDP_PROPERTIES_URL,
        },
        "virtual_devices": virtual_devices,
        "running_profiles": running,
        "profile_count": len(profiles),
    }
