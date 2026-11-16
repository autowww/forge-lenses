"""MJPEG preview streams for virtual camera profiles."""

from __future__ import annotations

import os
import subprocess
from typing import Any, Iterator

from lenses.virtual_camera.pipeline import build_preview_argv

_standalone_preview: dict[str, subprocess.Popen[Any]] = {}


def standalone_preview_pids() -> set[int]:
    pids: set[int] = set()
    for proc in _standalone_preview.values():
        if proc.poll() is None and proc.pid:
            pids.add(proc.pid)
    return pids


def stop_source_device_preview(device_path: str) -> None:
    dev = str(device_path or "").strip()
    if dev:
        stop_standalone_preview(f"__source__{dev}")


def register_standalone_preview(profile_id: str, proc: subprocess.Popen[Any]) -> None:
    old = _standalone_preview.get(profile_id)
    if old is not None and old.poll() is None:
        try:
            old.kill()
        except OSError:
            pass
    _standalone_preview[profile_id] = proc


def stop_standalone_preview(profile_id: str) -> None:
    proc = _standalone_preview.pop(profile_id, None)
    if proc is not None and proc.poll() is None:
        try:
            proc.kill()
        except OSError:
            pass


def start_standalone_preview(
    profile_id: str,
    device_path: str,
    width: int,
    height: int,
    *,
    formats: list[dict[str, Any]] | None = None,
    input_format: str = "MJPEG",
    fps: int = 15,
) -> subprocess.Popen[Any] | None:
    """Source preview when main pipeline is not running."""
    pid = str(profile_id or "").strip()
    dev = str(device_path or "").strip()
    if not pid or not dev:
        return None
    argv = build_preview_argv(dev, width, height, fps=fps, formats=formats, input_format=input_format)
    try:
        proc = subprocess.Popen(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
    except OSError:
        return None
    register_standalone_preview(pid, proc)
    return proc


def iter_mjpeg_from_fd(fd: int, chunk_size: int = 65536) -> Iterator[bytes]:
    while True:
        try:
            chunk = os.read(fd, chunk_size)
        except OSError:
            break
        if not chunk:
            break
        yield chunk


def iter_mjpeg_chunks(proc: subprocess.Popen[Any], chunk_size: int = 65536) -> Iterator[bytes]:
    if proc.stdout is None:
        return
    while True:
        if proc.poll() is not None:
            break
        try:
            chunk = proc.stdout.read(chunk_size)
        except OSError:
            break
        if not chunk:
            break
        yield chunk


def iter_profile_preview(profile_id: str, chunk_size: int = 65536) -> Iterator[bytes] | None:
    """Read MJPEG from owned pipeline tee branch (fan-out to HTTP clients)."""
    from lenses.virtual_camera.process_manager import iter_profile_preview as iter_preview_stream

    return iter_preview_stream(profile_id)
