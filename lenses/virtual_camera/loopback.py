"""v4l2loopback detection and bootstrap guidance (no silent privileged commands)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from lenses.virtual_camera.discovery import (
    _driver_name,
    _read_sysfs_name,
    _sysfs_video_nodes,
    discover_cameras,
    formats_for_device_path,
)
from lenses.virtual_camera.log import log_event
from lenses.virtual_camera.pipeline import list_ui_output_formats, vdi_friendly_formats


def _run(cmd: list[str], timeout: float = 10.0) -> tuple[int, str, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout or "", r.stderr or ""
    except (OSError, subprocess.TimeoutExpired) as ex:
        return 1, "", str(ex)


def module_installed() -> bool:
    code, out, _ = _run(["modinfo", "v4l2loopback"], timeout=8)
    return code == 0 and "v4l2loopback" in out


def module_loaded() -> bool:
    code, out, _ = _run(["lsmod"], timeout=5)
    if code != 0:
        return False
    for line in out.splitlines():
        if line.startswith("v4l2loopback"):
            return True
    return False


def _loopback_sysfs_devices() -> list[dict[str, Any]]:
    devices: list[dict[str, Any]] = []
    for node in _sysfs_video_nodes():
        driver = _driver_name(node)
        if driver != "v4l2loopback":
            continue
        device_path = f"/dev/{node.name}"
        label = _read_sysfs_name(node)
        exclusive_caps: bool | None = None
        cap_path = node / "exclusive_caps"
        if cap_path.is_file():
            try:
                exclusive_caps = cap_path.read_text(encoding="utf-8").strip() == "1"
            except OSError:
                exclusive_caps = None
        vf = formats_for_device_path(device_path)
        devices.append(
            {
                "device_path": device_path,
                "card_label": label,
                "exclusive_caps": exclusive_caps,
                "sysfs_node": str(node),
                "formats": vf,
                "output_format_options": list_ui_output_formats(vf),
                "vdi_friendly": vdi_friendly_formats(vf),
            }
        )
    return devices


def _card_label_arg(card_labels: list[str] | None = None) -> str:
    labels = card_labels or ["Studio Cam 1", "Studio Cam 2", "Studio Cam 3", "Studio Cam 4"]
    return ",".join(labels)


def privileged_commands(card_labels: list[str] | None = None) -> dict[str, str]:
    """Copy-paste shell commands for operators (Studio never runs these automatically)."""
    label_arg = _card_label_arg(card_labels)
    return {
        "install": (
            "sudo apt install -y v4l2loopback-dkms v4l-utils "
            "gstreamer1.0-tools gstreamer1.0-plugins-base "
            "gstreamer1.0-plugins-good gstreamer1.0-plugins-bad"
        ),
        "modprobe": (
            f"sudo modprobe v4l2loopback devices=4 exclusive_caps=1 "
            f"card_labels=\"{label_arg}\""
        ),
        "verify": "v4l2-ctl --list-devices",
        "persist": (
            f"echo 'options v4l2loopback devices=4 exclusive_caps=1 "
            f"card_labels=\"{label_arg}\"' | sudo tee /etc/modprobe.d/v4l2loopback.conf"
        ),
    }


def setup_issue(
    installed: bool,
    loaded: bool,
    has_devices: bool,
) -> str:
    if not installed:
        return "module_not_installed"
    if not loaded:
        return "module_not_loaded"
    if not has_devices:
        return "no_virtual_devices"
    return "ok"


def setup_issue_message(issue: str) -> str:
    messages = {
        "module_not_installed": (
            "The v4l2loopback kernel module package is not installed on this machine."
        ),
        "module_not_loaded": (
            "v4l2loopback is installed but not loaded — run the modprobe command below."
        ),
        "no_virtual_devices": (
            "v4l2loopback is loaded but no virtual camera devices were found — reload the module."
        ),
        "ok": "Virtual camera devices are ready.",
    }
    return messages.get(issue, "v4l2loopback setup is incomplete.")


def primary_sudo_command(installed: bool, loaded: bool) -> tuple[str, str]:
    cmds = privileged_commands()
    if not installed:
        return "install", cmds["install"]
    return "modprobe", cmds["modprobe"]


def setup_steps(card_labels: list[str] | None = None) -> list[str]:
    labels = card_labels or ["Studio Cam 1", "Studio Cam 2", "Studio Cam 3", "Studio Cam 4"]
    label_arg = _card_label_arg(labels)
    cmds = privileged_commands(labels)
    steps = [
        f"Install packages: {cmds['install']}",
        f"Load module (requires sudo): {cmds['modprobe']}",
        f"Optional persistence: {cmds['persist']}",
        f"Verify: {cmds['verify']}",
    ]
    return steps


def bootstrap_status() -> dict[str, Any]:
    installed = module_installed()
    loaded = module_loaded()
    loopback_devices = _loopback_sysfs_devices()
    disc = discover_cameras()
    virtual_from_discovery = disc.get("virtual") or []

    has_devices = bool(loopback_devices or virtual_from_discovery)
    issue = setup_issue(installed, loaded, has_devices)
    cmds = privileged_commands()
    action_key, primary_cmd = primary_sudo_command(installed, loaded)

    ready = installed and loaded and has_devices
    log_event(
        "loopback_state",
        module_installed=installed,
        module_loaded=loaded,
        device_count=len(loopback_devices),
    )
    return {
        "ok": True,
        "module_installed": installed,
        "module_loaded": loaded,
        "ready": ready,
        "loopback_devices": loopback_devices,
        "virtual_cameras": virtual_from_discovery,
        "gst_launch_available": disc.get("gst_launch_available"),
        "v4l2_ctl_available": disc.get("v4l2_ctl_available"),
        "setup_steps": setup_steps(),
        "setup_issue": issue if not ready else "ok",
        "setup_issue_message": setup_issue_message(issue if not ready else "ok"),
        "privileged_commands": cmds,
        "primary_sudo_command": primary_cmd,
        "primary_sudo_action": action_key,
        "privilege_note": (
            "Loading v4l2loopback requires root (sudo modprobe). "
            "Studio Desktop does not run privileged commands automatically."
        ),
    }


def suggest_virtual_device(used_paths: set[str]) -> str | None:
    """Pick an unused loopback device path if any exist."""
    status = bootstrap_status()
    candidates: list[str] = []
    for d in status.get("loopback_devices") or []:
        path = str(d.get("device_path") or "").strip()
        if path and path not in used_paths:
            candidates.append(path)
    for d in status.get("virtual_cameras") or []:
        path = str(d.get("device_path") or "").strip()
        if path and path not in used_paths:
            candidates.append(path)
    return candidates[0] if candidates else None
