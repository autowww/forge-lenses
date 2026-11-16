"""HTTP handlers for Virtual Camera Studio API."""

from __future__ import annotations

import urllib.parse
from pathlib import Path
from typing import Any, Callable, Iterator

from lenses.virtual_camera.discovery import (
    busy_message_for_camera,
    device_busy_info,
    discover_cameras,
    find_camera_by_stable_id,
    formats_for_device_path,
    terminate_device_holders,
)
from lenses.virtual_camera.errors import classify_busy_preflight
from lenses.virtual_camera.feature_flag import experimental_virtual_camera_enabled
from lenses.virtual_camera.loopback import bootstrap_status, suggest_virtual_device
from lenses.virtual_camera.pipeline import (
    build_gst_launch_argv,
    validate_virtual_output_format,
)
from lenses.virtual_camera.preview import (
    iter_mjpeg_chunks,
    iter_profile_preview,
    start_standalone_preview,
    stop_source_device_preview,
    stop_standalone_preview,
)
from lenses.virtual_camera.process_manager import (
    get_owned_pid,
    is_profile_owned,
    monitor_pipeline_startup,
    prepare_preview_pipe,
    reconcile_profile_runtime,
    start_pipeline,
    stop_all_processes,
    stop_profile_processes,
    wait_for_source_release,
)
from lenses.virtual_camera import profiles_store
from lenses.virtual_camera.runtime import (
    get_profile_runtime,
    mark_profile_stopped,
    set_profile_runtime,
    status_payload,
)

SendJson = Callable[[int, dict[str, Any]], None]


def _parse_profile_id(path: str, prefix: str) -> tuple[str, str] | None:
    if not path.startswith(prefix):
        return None
    rest = path[len(prefix):].strip("/")
    if not rest:
        return None
    parts = rest.split("/")
    return parts[0], "/".join(parts[1:]) if len(parts) > 1 else ""


def _runtime_enriched(workspace_root: Path, profile_id: str, rt: dict[str, Any]) -> dict[str, Any]:
    from lenses.virtual_camera.runtime import elapsed_seconds

    return {
        **rt,
        "elapsed_seconds": elapsed_seconds(rt.get("started_at")),
    }


def handle_get(
    workspace_root: Path,
    path: str,
    parsed: urllib.parse.ParseResult,
    *,
    send_json: SendJson,
) -> bool:
    if not experimental_virtual_camera_enabled():
        return False
    base = "/api/virtual-camera"
    if not path.startswith(base):
        return False

    if path == f"{base}/enabled":
        send_json(200, {"ok": True, "enabled": True})
        return True

    if path == f"{base}/cameras":
        send_json(200, discover_cameras())
        return True

    if path == f"{base}/bootstrap":
        send_json(200, bootstrap_status())
        return True

    if path == f"{base}/vdi-readiness":
        from lenses.virtual_camera.vdi import vdi_readiness_payload

        send_json(200, vdi_readiness_payload(workspace_root))
        return True

    if path == f"{base}/profiles":
        profiles = profiles_store.list_profiles(workspace_root)
        out = []
        for p in profiles:
            pid = str(p.get("id") or "")
            reconcile_profile_runtime(workspace_root, pid)
            rt = get_profile_runtime(workspace_root, pid)
            out.append({**p, "runtime": _runtime_enriched(workspace_root, pid, rt)})
        send_json(200, {"ok": True, "profiles": out})
        return True

    parsed_id = _parse_profile_id(path, f"{base}/profiles/")
    if parsed_id:
        profile_id, tail = parsed_id
        profile = profiles_store.get_profile(workspace_root, profile_id)
        if not profile:
            send_json(404, {"ok": False, "error": "not_found"})
            return True
        if tail == "status" or tail == "":
            send_json(200, status_payload(workspace_root, profile_id, profile))
            return True

    return False


def handle_preview_stream(
    workspace_root: Path,
    path: str,
    parsed: urllib.parse.ParseResult,
) -> tuple[int, str, Iterator[bytes]] | None:
    if not experimental_virtual_camera_enabled():
        return None
    base = "/api/virtual-camera/preview/"
    if not path.startswith(base):
        return None
    profile_id = path[len(base):].strip("/")
    if not profile_id:
        return (400, "text/plain; charset=utf-8", iter([b"bad profile id"]))

    qs = urllib.parse.parse_qs(parsed.query or "")

    if profile_id == "_source":
        device = str(qs.get("device", [""])[0] or "").strip()
        if not device:
            return (400, "text/plain; charset=utf-8", iter([b"missing device"]))
        try:
            w = int(qs.get("width", ["640"])[0] or 640)
            h = int(qs.get("height", ["360"])[0] or 360)
            fps = int(qs.get("fps", ["15"])[0] or 15)
        except (TypeError, ValueError):
            w, h, fps = 640, 360, 15
        input_format = str(qs.get("input_format", ["MJPEG"])[0] or "MJPEG")
        formats = formats_for_device_path(device)
        busy = device_busy_info(device)
        if busy.get("busy"):
            return (
                409,
                "text/plain; charset=utf-8",
                iter([b"camera busy - close other apps using this device"]),
            )
        preview_key = f"__source__{device}"
        proc = start_standalone_preview(
            preview_key,
            device,
            w,
            h,
            formats=formats,
            input_format=input_format,
            fps=fps,
        )
        if proc is None:
            return (500, "text/plain; charset=utf-8", iter([b"preview start failed"]))
        return (200, "multipart/x-mixed-replace; boundary=frame", iter_mjpeg_chunks(proc))

    profile = profiles_store.get_profile(workspace_root, profile_id)
    if not profile:
        return (404, "text/plain; charset=utf-8", iter([b"not found"]))

    qs = urllib.parse.parse_qs(parsed.query or "")
    view = str(qs.get("view", ["processed"])[0] or "processed").strip().lower()
    resolution = profile.get("resolution") or {}
    try:
        w = int(resolution.get("width") or 640)
        h = int(resolution.get("height") or 360)
    except (TypeError, ValueError):
        w, h = 640, 360

    rt = get_profile_runtime(workspace_root, profile_id)
    source_dev = str((profile.get("source") or {}).get("device_path") or "")
    virtual_dev = str((profile.get("virtual") or {}).get("device_path") or "")

    if view == "source":
        if rt.get("state") == "running":
            return (
                409,
                "text/plain; charset=utf-8",
                iter([b"source preview unavailable while pipeline running; use processed view"]),
            )
        if not source_dev:
            return (400, "text/plain; charset=utf-8", iter([b"missing source device"]))
        formats = formats_for_device_path(source_dev)
        input_format = str(profile.get("input_format") or "MJPEG")
        try:
            fps = int(profile.get("fps") or 15)
        except (TypeError, ValueError):
            fps = 15
        proc = start_standalone_preview(
            profile_id,
            source_dev,
            w,
            h,
            formats=formats,
            input_format=input_format,
            fps=fps,
        )
        if proc is None:
            return (500, "text/plain; charset=utf-8", iter([b"preview start failed"]))
        return (200, "multipart/x-mixed-replace; boundary=frame", iter_mjpeg_chunks(proc))

    if rt.get("state") != "running":
        return (409, "text/plain; charset=utf-8", iter([b"processed preview requires running pipeline"]))

    chunks = iter_profile_preview(profile_id)
    if chunks is None:
        return (500, "text/plain; charset=utf-8", iter([b"preview pipe unavailable"]))
    return (200, "multipart/x-mixed-replace; boundary=frame", chunks)


def handle_post(
    workspace_root: Path,
    path: str,
    body: dict[str, Any],
    *,
    send_json: SendJson,
) -> bool:
    if not experimental_virtual_camera_enabled():
        return False
    base = "/api/virtual-camera"
    if not path.startswith(base):
        return False

    if path == f"{base}/preview/stop":
        device = str(body.get("device") or "").strip()
        if device:
            stop_source_device_preview(device)
        send_json(200, {"ok": True})
        return True

    if path == f"{base}/profiles":
        incoming = body.get("profile") if isinstance(body.get("profile"), dict) else body
        if not isinstance(incoming, dict):
            send_json(400, {"ok": False, "error": "missing_profile"})
            return True
        used = {
            str((p.get("virtual") or {}).get("device_path") or "")
            for p in profiles_store.list_profiles(workspace_root)
        }
        virt = incoming.get("virtual") if isinstance(incoming.get("virtual"), dict) else {}
        if not str(virt.get("device_path") or "").strip():
            suggested = suggest_virtual_device(used)
            if suggested:
                incoming = {**incoming, "virtual": {**virt, "device_path": suggested}}
        profile = profiles_store.create_profile(workspace_root, incoming)
        send_json(200, {"ok": True, "profile": profile})
        return True

    parsed_id = _parse_profile_id(path, f"{base}/profiles/")
    if not parsed_id:
        return False
    profile_id, action = parsed_id
    profile = profiles_store.get_profile(workspace_root, profile_id)
    if not profile and action != "delete":
        send_json(404, {"ok": False, "error": "not_found"})
        return True

    if action == "start":
        _start_profile(workspace_root, profile_id, profile, send_json)
        return True
    if action == "stop":
        _stop_profile(workspace_root, profile_id)
        send_json(200, {"ok": True, "state": "stopped"})
        return True
    if action == "restart":
        _restart_profile(workspace_root, profile_id, profile, send_json, force=False)
        return True
    if action == "force-restart":
        if not body.get("confirm"):
            send_json(400, {"ok": False, "error": "confirm_required", "detail": "Set confirm=true to force restart."})
            return True
        _restart_profile(workspace_root, profile_id, profile, send_json, force=True)
        return True
    if action == "duplicate":
        dup = profiles_store.duplicate_profile(workspace_root, profile_id)
        if not dup:
            send_json(404, {"ok": False, "error": "not_found"})
        else:
            send_json(200, {"ok": True, "profile": dup})
        return True
    if action == "delete":
        _stop_profile(workspace_root, profile_id)
        profiles_store.delete_profile(workspace_root, profile_id)
        from lenses.virtual_camera.runtime import clear_profile_runtime

        clear_profile_runtime(workspace_root, profile_id)
        send_json(200, {"ok": True})
        return True

    return False


def handle_put(
    workspace_root: Path,
    path: str,
    body: dict[str, Any],
    *,
    send_json: SendJson,
) -> bool:
    if not experimental_virtual_camera_enabled():
        return False
    prefix = "/api/virtual-camera/profiles/"
    if not path.startswith(prefix):
        return False
    profile_id = path[len(prefix):].strip("/")
    if not profile_id or "/" in profile_id:
        return False
    incoming = body.get("profile") if isinstance(body.get("profile"), dict) else body
    if not isinstance(incoming, dict):
        send_json(400, {"ok": False, "error": "missing_profile"})
        return True
    updated = profiles_store.update_profile(workspace_root, profile_id, incoming)
    if not updated:
        send_json(404, {"ok": False, "error": "not_found"})
    else:
        send_json(200, {"ok": True, "profile": updated})
    return True


def shutdown(workspace_root: Path) -> None:
    stop_all_processes()


def _stop_profile(workspace_root: Path, profile_id: str) -> None:
    set_profile_runtime(workspace_root, profile_id, {"state": "stopping"})
    stop_profile_processes(profile_id)
    stop_standalone_preview(profile_id)
    mark_profile_stopped(workspace_root, profile_id)


def _restart_profile(
    workspace_root: Path,
    profile_id: str,
    profile: dict[str, Any],
    send_json: SendJson,
    *,
    force: bool,
) -> None:
    source_dev = str((profile.get("source") or {}).get("device_path") or "")
    set_profile_runtime(workspace_root, profile_id, {"state": "stopping"})
    stop_profile_processes(profile_id)
    stop_standalone_preview(profile_id)
    owned = get_owned_pid(profile_id)
    exclude = {owned} if owned else set()
    if force and source_dev:
        terminate_device_holders(source_dev, exclude_pids=exclude)
    if source_dev and not wait_for_source_release(source_dev, exclude_pids=exclude):
        classified = classify_busy_preflight()
        set_profile_runtime(
            workspace_root,
            profile_id,
            {
                "state": "error",
                "last_error": classified["message"],
                "error_code": classified["code"],
                "error_detail": classified["message"],
            },
        )
        send_json(
            400,
            {
                "ok": False,
                "error": "camera_busy",
                "error_code": classified["code"],
                "detail": classified["message"],
            },
        )
        return
    _start_profile(workspace_root, profile_id, profile, send_json)


def _start_profile(
    workspace_root: Path,
    profile_id: str,
    profile: dict[str, Any],
    send_json: SendJson,
) -> None:
    bootstrap = bootstrap_status()
    if not bootstrap.get("ready"):
        send_json(
            400,
            {
                "ok": False,
                "error": "loopback_not_ready",
                "detail": "v4l2loopback is not loaded or no virtual devices found.",
                "bootstrap": bootstrap,
            },
        )
        return

    source = profile.get("source") or {}
    virtual = profile.get("virtual") or {}
    source_dev = str(source.get("device_path") or "").strip()
    sink_dev = str(virtual.get("device_path") or "").strip()
    stable_id = str(source.get("stable_id") or "").strip()
    cam = find_camera_by_stable_id(stable_id) if stable_id else None
    if cam is None and source_dev:
        disc = discover_cameras()
        for c in disc.get("physical", []) + disc.get("virtual", []):
            if str(c.get("device_path") or "") == source_dev:
                cam = c
                break
    if cam and cam.get("busy") and not is_profile_owned(profile_id):
        msg = busy_message_for_camera(cam)
        classified = classify_busy_preflight()
        set_profile_runtime(
            workspace_root,
            profile_id,
            {
                "state": "error",
                "last_error": msg or classified["message"],
                "error_code": classified["code"],
                "error_detail": msg or classified["message"],
                "source_busy_holder": cam.get("busy_holders"),
            },
        )
        send_json(
            400,
            {
                "ok": False,
                "error": "camera_busy",
                "error_code": classified["code"],
                "detail": msg,
                "source_busy_holder": cam.get("busy_holders"),
            },
        )
        return

    virtual_formats = formats_for_device_path(sink_dev) if sink_dev else []
    output_err = validate_virtual_output_format(
        str(profile.get("output_format") or "YUYV"),
        virtual_formats,
    )
    if output_err:
        set_profile_runtime(
            workspace_root,
            profile_id,
            {
                "state": "error",
                "last_error": output_err,
                "error_code": "FORMAT_NEGOTIATION_FAILED",
                "error_detail": output_err,
            },
        )
        send_json(
            400,
            {
                "ok": False,
                "error": "format_negotiation_failed",
                "error_code": "FORMAT_NEGOTIATION_FAILED",
                "detail": output_err,
                "supported_fourccs": [
                    str(f.get("fourcc") or "")
                    for f in virtual_formats
                    if f.get("fourcc")
                ],
            },
        )
        return

    formats = cam.get("formats") if cam else None
    stop_profile_processes(profile_id)
    stop_standalone_preview(profile_id)

    pipe = prepare_preview_pipe(profile_id)
    if pipe is None:
        send_json(500, {"ok": False, "error": "preview_pipe_failed"})
        return
    read_fd, write_fd = pipe
    try:
        argv = build_gst_launch_argv(profile, formats, preview_fd=write_fd)
    except ValueError as ex:
        stop_profile_processes(profile_id)
        send_json(400, {"ok": False, "error": "invalid_profile", "detail": str(ex)})
        return

    try:
        proc = start_pipeline(
            workspace_root,
            profile_id,
            argv,
            preview_read_fd=read_fd,
            preview_write_fd=write_fd,
            input_device_path=source_dev,
            output_device_path=sink_dev,
        )
    except OSError as ex:
        stop_profile_processes(profile_id)
        send_json(500, {"ok": False, "error": "spawn_failed", "detail": str(ex)})
        return

    ok, err = monitor_pipeline_startup(workspace_root, profile_id, proc)
    if not ok:
        classified = classify_busy_preflight() if err and "busy" in (err or "").lower() else None
        send_json(
            500,
            {
                "ok": False,
                "error": "pipeline_failed",
                "error_code": classified["code"] if classified else get_profile_runtime(workspace_root, profile_id).get("error_code"),
                "detail": err,
            },
        )
        return
    send_json(200, status_payload(workspace_root, profile_id, profile))
