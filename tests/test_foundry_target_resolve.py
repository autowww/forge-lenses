"""Tests for Foundry target resolution."""

from pathlib import Path

import pytest


@pytest.fixture
def ws(tmp_path):
    proj = tmp_path / "forge-df-test-project"
    (proj / "src" / "dfcalc").mkdir(parents=True)
    (proj / "src" / "dfcalc" / "engine.py").write_text("", encoding="utf-8")
    return tmp_path


def test_resolve_project_and_file_hint(ws: Path):
    from lenses.foundry.target_resolve import resolve_foundry_target

    repo, hint = resolve_foundry_target(
        ws,
        {
            "project": "forge-df-test-project",
            "target": "src/dfcalc/engine.py",
        },
    )
    assert repo == (ws / "forge-df-test-project").resolve()
    assert hint == "src/dfcalc/engine.py"
