"""Foundry intake parser."""

from lenses.foundry.intake import parse_intake_message


def test_multiply_intake():
    out = parse_intake_message("please fix failing multiply for @forge-df-test-project #src/dfcalc/engine.py L1")
    assert out["goal"] == "fix failing multiply"
    assert out["level"] == "L1"
    assert out["project"] == "forge-df-test-project"
