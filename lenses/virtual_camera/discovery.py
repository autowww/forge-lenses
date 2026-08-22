"""Discover physical and virtual V4L2 cameras on Linux."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

from lenses.virtual_camera.log import log_event

_DEVICE_LINE = re.compile(r"^(/dev/video\d+)\s*$")
_GROUP_HEADER = re.compile(r"^(.+?)\s*\(([^)]+)\):\s*$")
_FORMAT_LINE = re.compile(
    r"^\s*\[\d+\]:\s*'([^']+)'\s*(.*)$"
)
_SIZE_LINE = re.compile(r"^\s*Size:\s*Discrete\s+(\d+)x(\d+)")
_SIZE_CONTINUOUS_LINE = re.compile(
    r"^\s*Size:\s*Continuous\s+(\d+)x(\d+)\s*-\s*(\d+)x(\d+)"
)
_INTERVAL_LINE = re.compile(r"^\s*Interval:\s*Discrete\s+([\d.]+)fps")


def _run(cmd: list[str], timeout: float = 15.0) -> tuple[int, str, str]:
    try:
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return r.returncode, r.stdout or "", r.stderr or ""
    except (OSError, subprocess.TimeoutExpired) as ex:
        return 1, "", str(ex)


def v4l2_ctl_available() -> bool:
    code, _, _ = _run(["v4l2-ctl", "--version"], timeout=5)
    return code == 0


def gst_launch_available() -> bool:
    code, _, _ = _run(["gst-launch-1.0", "--version"], timeout=5)
    return code == 0


def _sysfs_video_nodes() -> list[Path]:
    base = Path("/sys/class/video4linux")
    if not base.is_dir():
        return []
    return sorted(base.glob("video*"), key=lambda p: p.name)


def _read_sysfs_name(node: Path) -> str:
    name_path = node / "name"
    try:
        return name_path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _driver_name_from_sysfs(node: Path) -> str:
    try:
        dev_link = node / "device" / "driver"
        if dev_link.is_symlink():
            return Path(dev_link).name
    except OSError:
        pass
    return ""


def _driver_name_from_v4l2(device_path: str) -> str:
    code, out, _ = _run(["v4l2-ctl", "-d", device_path, "--all"], timeout=6)
    if code != 0:
        return ""
    for line in out.splitlines():
        if "Driver name" in line and "loopback" in line.lower():
            return "v4l2loopback"
    return ""


def _driver_name(node: Path) -> str:
    """Sysfs driver symlink when present; v4l2loopback nodes often lack device/driver."""
    driver = _driver_name_from_sysfs(node)
    if driver:
        return driver
    return _driver_name_from_v4l2(_device_path_for_node(node))


def _is_virtual_device(node: Path, grouped_meta: dict[str, Any]) -> bool:
    if _driver_name(node) == "v4l2loopback":
        return True
    bus = str(grouped_meta.get("bus_info") or "")
    return "v4l2loopback" in bus


def _device_path_for_node(node: Path) -> str:
    return f"/dev/{node.name}"


def _udev_properties(device_path: str) -> dict[str, str]:
    code, out, _ = _run(["udevadm", "info", "--query=property", f"--name={device_path}"], timeout=8)
    props: dict[str, str] = {}
    if code != 0:
        return props
    for line in out.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            props[k.strip()] = v.strip()
    return props


def stable_id_for_device(device_path: str, label: str, driver: str) -> str:
    props = _udev_properties(device_path)
    vendor = props.get("ID_VENDOR_ID") or props.get("ID_USB_VENDOR_ID") or ""
    product = props.get("ID_MODEL_ID") or props.get("ID_USB_MODEL_ID") or ""
    serial = props.get("ID_SERIAL_SHORT") or props.get("ID_SERIAL") or ""
    path_id = props.get("ID_PATH") or props.get("DEVPATH") or ""
    if vendor or product:
        return f"usb:{vendor}:{product}:{serial}:{path_id}"
    if driver == "v4l2loopback":
        return f"loopback:{device_path}:{label}"
    return f"name:{label}:{path_id or device_path}"


def device_busy_info(device_path: str, exclude_pids: set[int] | None = None) -> dict[str, Any]:
    code, out, _ = _run(["fuser", device_path], timeout=8)
    if code != 0 and not out.strip():
        return {"busy": False, "holders": []}
    ex = exclude_pids or set()
    holders: list[dict[str, str]] = []
    for line in out.splitlines():
        parts = line.split()
        if not parts:
            continue
        try:
            pid = int(parts[0])
        except ValueError:
            continue
        if pid in ex:
            continue
        cmd = ""
        if len(parts) > 1:
            cmd = " ".join(parts[1:])
        holders.append({"pid": pid, "command": cmd})
    return {"busy": bool(holders), "holders": holders}


def is_device_busy(device_path: str, exclude_pids: set[int] | None = None) -> bool:
    info = device_busy_info(device_path)
    if not info.get("busy"):
        return False
    ex = exclude_pids or set()
    for h in info.get("holders") or []:
        try:
            pid = int(h.get("pid") or 0)
        except (TypeError, ValueError):
            continue
        if pid and pid not in ex:
            return True
    return False


def wait_until_device_free(
    device_path: str,
    *,
    timeout_ms: int = 2000,
    poll_ms: int = 100,
    exclude_pids: set[int] | None = None,
) -> bool:
    import time

    dev = str(device_path or "").strip()
    if not dev:
        return True
    deadline = time.time() + (timeout_ms / 1000.0)
    while time.time() < deadline:
        if not is_device_busy(dev, exclude_pids=exclude_pids):
            return True
        time.sleep(poll_ms / 1000.0)
    return not is_device_busy(dev, exclude_pids=exclude_pids)


def terminate_device_holders(
    device_path: str,
    *,
    exclude_pids: set[int] | None = None,
    term_timeout_s: float = 2.0,
) -> list[int]:
    """SIGTERM then SIGKILL specific PIDs holding the device — never fuser -k."""
    import os
    import signal
    import time

    dev = str(device_path or "").strip()
    if not dev:
        return []
    info = device_busy_info(dev)
    ex = exclude_pids or set()
    targeted: list[int] = []
    for h in info.get("holders") or []:
        try:
            pid = int(h.get("pid") or 0)
        except (TypeError, ValueError):
            continue
        if not pid or pid in ex:
            continue
        targeted.append(pid)
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
    if not targeted:
        return []
    deadline = time.time() + term_timeout_s
    while time.time() < deadline:
        if not is_device_busy(dev, exclude_pids=ex):
            return targeted
        time.sleep(0.1)
    for pid in targeted:
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
    return targeted


def parse_list_devices_output(text: str) -> list[dict[str, Any]]:
    """Parse ``v4l2-ctl --list-devices`` grouped output."""
    groups: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in text.splitlines():
        m_hdr = _GROUP_HEADER.match(line)
        if m_hdr:
            if current:
                groups.append(current)
            current = {
                "label": m_hdr.group(1).strip(),
                "bus_info": m_hdr.group(2).strip(),
                "devices": [],
            }
            continue
        m_dev = _DEVICE_LINE.match(line.strip())
        if m_dev and current is not None:
            current["devices"].append(m_dev.group(1))
    if current:
        groups.append(current)
    return groups


def parse_formats_ext(text: str) -> list[dict[str, Any]]:
    formats: list[dict[str, Any]] = []
    current_fmt: dict[str, Any] | None = None
    current_size: dict[str, Any] | None = None
    for line in text.splitlines():
        m_fmt = _FORMAT_LINE.match(line)
        if m_fmt:
            if current_fmt:
                formats.append(current_fmt)
            current_fmt = {
                "fourcc": m_fmt.group(1),
                "description": m_fmt.group(2).strip(),
                "sizes": [],
            }
            current_size = None
            continue
        m_size = _SIZE_LINE.match(line)
        if m_size and current_fmt is not None:
            current_size = {
                "width": int(m_size.group(1)),
                "height": int(m_size.group(2)),
                "fps": [],
            }
            current_fmt["sizes"].append(current_size)
            continue
        m_cont = _SIZE_CONTINUOUS_LINE.match(line)
        if m_cont and current_fmt is not None:
            current_size = {
                "width": int(m_cont.group(3)),
                "height": int(m_cont.group(4)),
                "min_width": int(m_cont.group(1)),
                "min_height": int(m_cont.group(2)),
                "fps": [],
                "continuous": True,
            }
            current_fmt["sizes"].append(current_size)
            continue
        m_int = _INTERVAL_LINE.match(line)
        if m_int and current_size is not None:
            try:
                fps = float(m_int.group(1))
                current_size["fps"].append(fps)
            except ValueError:
                pass
    if current_fmt:
        formats.append(current_fmt)
    return formats


def enumerate_device(device_path: str, label: str, driver: str, is_virtual: bool) -> dict[str, Any]:
    from lenses.virtual_camera.preview import standalone_preview_pids

    stable_id = stable_id_for_device(device_path, label, driver)
    busy = device_busy_info(device_path, exclude_pids=standalone_preview_pids())
    formats: list[dict[str, Any]] = []
    fmt_cmd = (
        ["v4l2-ctl", "-d", device_path, "--list-formats-out-ext"]
        if is_virtual
        else ["v4l2-ctl", "-d", device_path, "--list-formats-ext"]
    )
    code, out, err = _run(fmt_cmd, timeout=12)
    if code == 0:
        formats = parse_formats_ext(out)
    else:
        log_event("camera_formats_failed", device=device_path, detail=(err or out)[:500])
    if is_virtual and not formats:
        code2, out2, err2 = _run(
            ["v4l2-ctl", "-d", device_path, "--list-formats-ext"],
            timeout=12,
        )
        if code2 == 0:
            formats = parse_formats_ext(out2)
        elif not err:
            log_event(
                "camera_formats_failed",
                device=device_path,
                detail=(err2 or out2)[:500],
            )
    return {
        "device_path": device_path,
        "label": label,
        "stable_id": stable_id,
        "driver": driver,
        "is_virtual": is_virtual,
        "busy": busy["busy"],
        "busy_holders": busy["holders"],
        "formats": formats,
    }


def discover_cameras() -> dict[str, Any]:
    if not v4l2_ctl_available():
        log_event("camera_discovery_skipped", reason="v4l2_ctl_missing")
        return {
            "ok": True,
            "v4l2_ctl_available": False,
            "gst_launch_available": gst_launch_available(),
            "physical": [],
            "virtual": [],
            "error": "v4l2-ctl not found. Install v4l-utils.",
        }

    grouped: dict[str, dict[str, Any]] = {}
    code, out, _ = _run(["v4l2-ctl", "--list-devices"], timeout=15)
    if code == 0:
        for g in parse_list_devices_output(out):
            label = str(g.get("label") or "")
            for dev in g.get("devices") or []:
                grouped[str(dev)] = {"label": label, "bus_info": g.get("bus_info")}

    physical: list[dict[str, Any]] = []
    virtual: list[dict[str, Any]] = []
    for node in _sysfs_video_nodes():
        device_path = _device_path_for_node(node)
        meta = grouped.get(device_path, {})
        driver = _driver_name(node)
        is_virtual = _is_virtual_device(node, meta)
        if is_virtual and driver != "v4l2loopback":
            driver = "v4l2loopback"
        label = str(meta.get("label") or _read_sysfs_name(node) or device_path)
        cam = enumerate_device(device_path, label, driver, is_virtual)
        if meta.get("bus_info"):
            cam["bus_info"] = meta["bus_info"]
        if is_virtual:
            virtual.append(cam)
        elif cam.get("formats"):
            physical.append(cam)

    log_event(
        "camera_discovered",
        physical_count=len(physical),
        virtual_count=len(virtual),
    )
    return {
        "ok": True,
        "v4l2_ctl_available": True,
        "gst_launch_available": gst_launch_available(),
        "physical": physical,
        "virtual": virtual,
    }


def formats_for_device_path(device_path: str) -> list[dict[str, Any]]:
    dev = str(device_path or "").strip()
    if not dev:
        return []
    data = discover_cameras()
    for cam in data.get("physical", []) + data.get("virtual", []):
        if str(cam.get("device_path") or "") == dev:
            fmts = cam.get("formats")
            return fmts if isinstance(fmts, list) else []
    return []


def find_camera_by_stable_id(stable_id: str) -> dict[str, Any] | None:
    sid = str(stable_id or "").strip()
    if not sid:
        return None
    data = discover_cameras()
    for cam in data.get("physical", []) + data.get("virtual", []):
        if str(cam.get("stable_id") or "") == sid:
            return cam
    return None


def busy_message_for_camera(cam: dict[str, Any]) -> str | None:
    if not cam.get("busy"):
        return None
    label = str(cam.get("label") or cam.get("device_path") or "Camera")
    holders = cam.get("busy_holders") or []
    if holders:
        h = holders[0]
        cmd = str(h.get("command") or "").strip()
        if cmd:
            return f"{label} is currently being used by another application ({cmd})."
    return f"{label} is currently being used by another application."
