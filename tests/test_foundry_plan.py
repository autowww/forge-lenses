"""Foundry plan API."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def ws(tmp_path):
    root = tmp_path / "ws"
    target = root / "proj"
    (target / "src" / "dfcalc").mkdir(parents=True)
    (target / "src" / "dfcalc" / "engine.py").write_text("", encoding="utf-8")
    return root


def test_build_plan_multiply(ws: Path):
    from lenses.foundry.plan import build_plan

    target = ws / "proj"
    out = build_plan(
        {"goal": "fix failing multiply", "target": str(target), "level": "L1"},
        ws,
    )
    assert out["ok"] is True
    assert out["units"][0]["allowed_files"] == ["src/dfcalc/engine.py"]


def test_build_plan_rejects_l2(ws: Path):
    from lenses.foundry.plan import build_plan

    target = ws / "proj"
    out = build_plan({"goal": "x", "target": str(target), "level": "L2"}, ws)
    assert out.get("ok") is False
