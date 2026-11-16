"""Own and terminate GStreamer pipeline subprocesses per profile."""

from __future__ import annotations

import os
import queue
import signal
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from pathlib import Path
from typing import Any, Iterator

from lenses.virtual_camera.discovery import wait_until_device_free
from lenses.virtual_camera.errors import classify_gst_stderr
from lenses.virtual_camera.log import log_event
from lenses.virtual_camera.runtime import set_profile_runtime

_lock = threading.Lock()
_handles: dict[str, dict[str, Any]] = {}

TERMINATE_TIMEOUT_S = 3.0
DEVICE_RELEASE_TIMEOUT_MS = 2000
DEVICE_RELEASE_POLL_MS = 100
_PREVIEW_BOUNDARY = b"--frame"
_PREVIEW_HEADER_END = b"\r\n\r\n"


def _format_mjpeg_part(jpeg: bytes) -> bytes:
    header = (
        b"--frame\r\n"
        b"Content-Type: image/jpeg\r\n"
        + f"Content-Length: {len(jpeg)}\r\n\r\n".encode("ascii")
        + jpeg
        + b"\r\n"
    )
    return header


def _extract_complete_jpeg_frames(buf: bytearray) -> list[bytes]:
    """Parse multipart MJPEG chunks from GStreamer fdsink."""
    frames: list[bytes] = []
    while True:
        start = buf.find(_PREVIEW_BOUNDARY)
        if start == -1:
            break
        if start > 0:
            del buf[:start]
            start = 0
        header_end = buf.find(_PREVIEW_HEADER_END, start)
        if header_end == -1:
            break
        header = bytes(buf[start:header_end])
        content_length: int | None = None
        for line in header.split(b"\r\n"):
            if line.lower().startswith(b"content-length:"):
                try:
                    content_length = int(line.split(b":", 1)[1].strip())
                except (ValueError, IndexError):
                    content_length = None
        if content_length is None or content_length <= 0:
            break
        body_start = header_end + len(_PREVIEW_HEADER_END)
        body_end = body_start + content_length
        if len(buf) < body_end:
            break
        frames.append(bytes(buf[body_start:body_end]))
        consume_end = body_end
        if len(buf) >= body_end + 2 and buf[body_end:body_end + 2] == b"\r\n":
            consume_end = body_end + 2
        del buf[:consume_end]
    return frames


def _preview_fanout_loop(profile_id: str, read_fd: int) -> None:
    buf = bytearray()
    try:
        while True:
            try:
                chunk = os.read(read_fd, 65536)
            except OSError:
                break
            if not chunk:
                break
            buf.extend(chunk)
            for frame in _extract_complete_jpeg_frames(buf):
                with _lock:
                    h = _handles.get(profile_id) or {}
                    subs = h.get("preview_subscribers")
                    if not subs:
                        continue
                    for sub in list(subs):
                        try:
                            sub.put_nowait(frame)
                        except queue.Full:
                            try:
                                sub.get_nowait()
                            except queue.Empty:
                                pass
                            try:
                                sub.put_nowait(frame)
                            except queue.Full:
                                pass
    finally:
        try:
            os.close(read_fd)
        except OSError:
            pass
        with _lock:
            h = _handles.get(profile_id) or {}
            h.pop("preview_read_fd", None)


def _start_preview_fanout(profile_id: str, read_fd: int) -> None:
    with _lock:
        h = _handles.get(profile_id) or {}
        if h.get("preview_fanout_thread") is not None:
            return
    thread = threading.Thread(
        target=_preview_fanout_loop,
        args=(profile_id, int(read_fd)),
        name=f"vc-preview-fanout:{profile_id}",
        daemon=True,
    )
    with _lock:
        entry = _handles.setdefault(profile_id, {})
        entry["preview_fanout_thread"] = thread
        entry.setdefault("preview_subscribers", set())
    thread.start()


def _stop_preview_fanout(profile_id: str, *, close_fd: bool = True) -> None:
    with _lock:
        h = _handles.get(profile_id) or {}
        thread = h.get("preview_fanout_thread")
        read_fd = h.get("preview_read_fd")
        subs = h.get("preview_subscribers")
        # Drop fan-out first so HTTP preview streams exit without waiting on queue.get.
        h.pop("preview_fanout_thread", None)
        if subs:
            subs.clear()
    if close_fd and read_fd is not None:
        try:
            os.close(int(read_fd))
        except OSError:
            pass
    if thread is not None and thread.is_alive():
        thread.join(timeout=2.0)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _apply_pipeline_error(
    workspace_root: Path,
    profile_id: str,
    err_text: str,
    *,
    state: str = "error",
) -> None:
    classified = classify_gst_stderr(err_text)
    set_profile_runtime(
        workspace_root,
        profile_id,
        {
            "state": state,
            "last_error": classified["message"],
            "error_code": classified["code"],
            "error_detail": classified["message"],
            "stderr_tail": classified["raw"],
        },
    )


def _close_preview_pipe(profile_id: str) -> None:
    _stop_preview_fanout(profile_id)
    with _lock:
        h = _handles.get(profile_id) or {}
        for key in ("preview_read_fd", "preview_write_fd"):
            fd = h.get(key)
            if fd is not None:
                try:
                    os.close(int(fd))
                except OSError:
                    pass
            h.pop(key, None)


def _terminate_proc(proc: subprocess.Popen[Any] | None, label: str) -> None:
    if proc is None:
        return
    if proc.poll() is not None:
        return
    try:
        if proc.pid:
            os.killpg(proc.pid, signal.SIGTERM)
    except OSError:
        try:
            proc.terminate()
        except OSError:
            pass
    try:
        proc.wait(timeout=TERMINATE_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        try:
            if proc.pid:
                os.killpg(proc.pid, signal.SIGKILL)
        except OSError:
            try:
                proc.kill()
            except OSError:
                pass
        try:
            proc.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            pass
    if proc.stderr is not None:
        try:
            proc.stderr.close()
        except OSError:
            pass
    log_event("pipeline_stop", label=label, pid=proc.pid, returncode=proc.poll())


def _gst_child_pids() -> list[int]:
    """gst-launch children of this process (virtual camera pipelines)."""
    parent = os.getpid()
    try:
        out = subprocess.check_output(
            ["pgrep", "-P", str(parent)],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        child_pids = [int(x) for x in out.split() if x.strip().isdigit()]
    except (OSError, subprocess.CalledProcessError, ValueError):
        return []
    result: list[int] = []
    for pid in child_pids:
        cmdline_path = Path(f"/proc/{pid}/cmdline")
        try:
            cmd = cmdline_path.read_bytes().replace(b"\0", b" ").decode("utf-8", errors="replace")
        except OSError:
            continue
        if "gst-launch" in cmd and "v4l2" in cmd:
            result.append(pid)
    return result


def kill_orphan_gst_pipelines() -> None:
    for pid in _gst_child_pids():
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass


def reconcile_profile_runtime(workspace_root: Path, profile_id: str) -> None:
    """Clear stale starting/running/stopping when no owned process exists."""
    from lenses.virtual_camera.runtime import get_profile_runtime, mark_profile_stopped

    rt = get_profile_runtime(workspace_root, profile_id)
    state = str(rt.get("state") or "stopped").lower()
    if state not in ("running", "starting", "stopping"):
        return
    if is_profile_owned(profile_id):
        return
    kill_orphan_gst_pipelines()
    mark_profile_stopped(workspace_root, profile_id)


def stop_profile_processes(profile_id: str) -> None:
    pid = str(profile_id or "").strip()
    with _lock:
        h = dict(_handles.get(pid) or {})
    # Close preview fan-out before terminating gst so fdsink does not block shutdown.
    _close_preview_pipe(pid)
    _terminate_proc(h.get("proc"), f"pipeline:{pid}")
    with _lock:
        _handles.pop(pid, None)


def stop_all_processes() -> None:
    with _lock:
        ids = list(_handles.keys())
    for profile_id in ids:
        stop_profile_processes(profile_id)


def get_owned_pid(profile_id: str) -> int | None:
    with _lock:
        h = _handles.get(profile_id) or {}
        proc = h.get("proc")
        if proc is not None and proc.poll() is None and proc.pid:
            return int(proc.pid)
    return None


def get_preview_read_fd(profile_id: str) -> int | None:
    with _lock:
        h = _handles.get(profile_id) or {}
        if h.get("preview_fanout_thread") is None:
            return None
        proc = h.get("proc")
        if proc is None or proc.poll() is not None:
            return None
        return 1  # sentinel: fan-out active


def subscribe_profile_preview(profile_id: str) -> queue.Queue[bytes]:
    q: queue.Queue[bytes] = queue.Queue(maxsize=4)
    with _lock:
        entry = _handles.setdefault(profile_id, {})
        subs = entry.setdefault("preview_subscribers", set())
        subs.add(q)
    return q


def unsubscribe_profile_preview(profile_id: str, sub: queue.Queue[bytes]) -> None:
    with _lock:
        h = _handles.get(profile_id) or {}
        subs = h.get("preview_subscribers")
        if subs:
            subs.discard(sub)


def iter_profile_preview(profile_id: str) -> Iterator[bytes] | None:
    """MJPEG multipart stream for HTTP; fans out to multiple browser clients."""
    if get_preview_read_fd(profile_id) is None:
        return None
    sub = subscribe_profile_preview(profile_id)

    def _gen() -> Iterator[bytes]:
        try:
            while get_preview_read_fd(profile_id) is not None:
                try:
                    frame = sub.get(timeout=5.0)
                except queue.Empty:
                    continue
                yield _format_mjpeg_part(frame)
        finally:
            unsubscribe_profile_preview(profile_id, sub)

    return _gen()


def start_pipeline(
    workspace_root: Path,
    profile_id: str,
    argv: list[str],
    *,
    preview_read_fd: int | None = None,
    preview_write_fd: int | None = None,
    input_device_path: str | None = None,
    output_device_path: str | None = None,
) -> subprocess.Popen[Any]:
    """Spawn gst-launch in its own process group."""
    pass_fds: tuple[int, ...] = ()
    if preview_write_fd is not None:
        pass_fds = (int(preview_write_fd),)
    elif preview_read_fd is not None:
        with _lock:
            wfd = (_handles.get(profile_id) or {}).get("preview_write_fd")
        if wfd is not None:
            pass_fds = (int(wfd),)

    popen_kwargs: dict[str, Any] = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.PIPE,
        "start_new_session": True,
    }
    if pass_fds:
        popen_kwargs["pass_fds"] = pass_fds

    proc = subprocess.Popen(argv, **popen_kwargs)
    if preview_write_fd is not None:
        try:
            os.close(int(preview_write_fd))
        except OSError:
            pass

    fanout_read_fd: int | None = None
    with _lock:
        entry = _handles.setdefault(profile_id, {})
        entry["proc"] = proc
        if preview_read_fd is not None:
            entry["preview_read_fd"] = preview_read_fd
            entry.pop("preview_write_fd", None)
            fanout_read_fd = preview_read_fd
        else:
            entry.pop("preview_write_fd", None)

    if fanout_read_fd is not None:
        _start_preview_fanout(profile_id, fanout_read_fd)

    set_profile_runtime(
        workspace_root,
        profile_id,
        {
            "state": "starting",
            "pid": proc.pid,
            "started_at": _now_iso(),
            "last_error": None,
            "error_code": None,
            "error_detail": None,
            "stderr_tail": None,
            "source_busy_holder": None,
            "input_device_path": input_device_path,
            "output_device_path": output_device_path,
        },
    )
    log_event("pipeline_start", profile_id=profile_id, pid=proc.pid, argv=" ".join(argv))
    return proc


def prepare_preview_pipe(profile_id: str) -> tuple[int, int] | None:
    """Create pipe for tee MJPEG branch. Returns (read_fd, write_fd) for parent/child."""
    try:
        read_fd, write_fd = os.pipe()
    except OSError:
        return None
    with _lock:
        entry = _handles.setdefault(profile_id, {})
        entry["preview_read_fd"] = read_fd
        entry["preview_write_fd"] = write_fd
    return read_fd, write_fd


def monitor_pipeline_startup(
    workspace_root: Path,
    profile_id: str,
    proc: subprocess.Popen[Any],
    *,
    wait_s: float = 1.5,
) -> tuple[bool, str | None]:
    """Wait briefly and detect immediate failure."""
    time.sleep(wait_s)
    code = proc.poll()
    if code is not None:
        err_text = ""
        try:
            if proc.stderr is not None:
                stderr = proc.stderr.read()
                if stderr:
                    err_text = stderr.decode("utf-8", errors="replace")[:2000]
        except (OSError, ValueError):
            pass
        if not err_text.strip():
            err_text = f"exit code {code}"
        _apply_pipeline_error(workspace_root, profile_id, err_text)
        log_event("gst_error", profile_id=profile_id, detail=err_text[:500], returncode=code)
        stop_profile_processes(profile_id)
        return False, err_text
    set_profile_runtime(workspace_root, profile_id, {"state": "running"})
    return True, None


def wait_for_source_release(
    device_path: str,
    *,
    exclude_pids: set[int] | None = None,
) -> bool:
    return wait_until_device_free(
        device_path,
        timeout_ms=DEVICE_RELEASE_TIMEOUT_MS,
        poll_ms=DEVICE_RELEASE_POLL_MS,
        exclude_pids=exclude_pids,
    )


def is_profile_owned(profile_id: str) -> bool:
    with _lock:
        h = _handles.get(profile_id)
        if not h:
            return False
        proc = h.get("proc")
        return proc is not None and proc.poll() is None
