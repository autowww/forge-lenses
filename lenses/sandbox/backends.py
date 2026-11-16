"""Sandbox backend selection (inline, subprocess, Docker)."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

BackendName = Literal["inline", "process", "docker"]


def docs_health_step_backend() -> BackendName:
    raw = str(os.environ.get("LENSES_DOCS_HEALTH_STEP_BACKEND") or "").strip().lower()
    if raw in ("process", "subprocess", "isolated"):
        return "process"
    if raw == "docker":
        return "docker"
    if raw in ("inline", "sync"):
        return "inline"
    # Primary path: Docker when the CLI is available; otherwise inline (dev / CI without Docker).
    if docker_cli_available():
        return "docker"
    return "inline"


def docker_cli_available() -> bool:
    return shutil.which("docker") is not None


@dataclass
class DockerStepSpec:
    workspace_root: Path
    lenses_repo_root: Path
    argv_tail: list[str]


def build_docker_run_command(spec: DockerStepSpec) -> list[str]:
    """
    Build a ``docker run`` argv for running the step CLI inside a container.

    Mounts the workspace read-only at ``/workspace`` and the Lenses package tree
    read-only at ``/lenses-src``; writes go to ``/workspace/.lenses-local`` only
    on the host (still part of workspace — operator should treat that as local state).

    Image must include Python 3 and dependencies; override with ``LENSES_SANDBOX_IMAGE``.
    """
    img = str(os.environ.get("LENSES_SANDBOX_IMAGE") or "python:3.12-slim")
    ws = spec.workspace_root.resolve()
    lr = spec.lenses_repo_root.resolve()
    return [
        "docker",
        "run",
        "--rm",
        "-i",
        "-v",
        f"{ws}:/workspace:rw",
        "-v",
        f"{lr}:/lenses-src:ro",
        "-w",
        "/lenses-src",
        "-e",
        "PYTHONPATH=/lenses-src",
        img,
        "python",
        "-m",
        "lenses.docs_health.step_cli",
        *spec.argv_tail,
    ]


def start_docker_step(spec: DockerStepSpec) -> subprocess.Popen[Any]:
    cmd = build_docker_run_command(spec)
    return subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def extract_container_id_from_docker_run(proc: subprocess.Popen[Any]) -> str | None:
    """Best-effort: Docker CLI does not echo container id for foreground ``docker run``."""
    return None
