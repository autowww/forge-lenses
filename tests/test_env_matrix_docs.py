"""``docs/strategy/env-matrix.yaml`` entries must appear in config-env.md."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
MATRIX = REPO_ROOT / "docs" / "strategy" / "env-matrix.yaml"
CONFIG_ENV = REPO_ROOT / "docs" / "reference" / "config-env.md"


def test_env_matrix_variables_documented_in_config_env() -> None:
    data = yaml.safe_load(MATRIX.read_text(encoding="utf-8"))
    assert data.get("version") == 1
    vars_ = data["variables"]
    text = CONFIG_ENV.read_text(encoding="utf-8")
    for entry in vars_:
        name = entry["name"]
        assert name in text, f"{name} missing from {CONFIG_ENV.relative_to(REPO_ROOT)}"
