"""Sandbox backends — process and Docker execution handles with physical stop."""

from __future__ import annotations

from lenses.sandbox.active import (
    clear_session_handles,
    register_docker_container,
    register_subprocess,
    stop_session_execution,
)
from lenses.sandbox.docker_runner import (
    build_docs_health_docker_argv,
    docker_inspect_status,
    docker_kill,
    docker_stop,
    patch_tasklet_sandbox,
    sandbox_cidfile_path,
    tasklet_checkpoint_dir,
)

__all__ = [
    "build_docs_health_docker_argv",
    "clear_session_handles",
    "docker_inspect_status",
    "docker_kill",
    "docker_stop",
    "patch_tasklet_sandbox",
    "register_docker_container",
    "register_subprocess",
    "sandbox_cidfile_path",
    "stop_session_execution",
    "tasklet_checkpoint_dir",
]
