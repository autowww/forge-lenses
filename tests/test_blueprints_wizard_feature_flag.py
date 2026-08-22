"""Tests for Blueprints Wizard server feature flag (no HTTP server)."""

from __future__ import annotations

import pytest

from lenses.blueprints_wizard.feature_flag import experimental_blueprints_wizard_enabled


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1", True),
        ("true", True),
        ("TRUE", True),
        ("yes", True),
        ("on", True),
        ("", True),
        ("0", False),
        ("false", False),
        ("no", False),
        ("off", False),
    ],
)
def test_experimental_blueprints_wizard_enabled(
    monkeypatch: pytest.MonkeyPatch, value: str, expected: bool
) -> None:
    monkeypatch.setenv("LENSES_EXPERIMENTAL_BLUEPRINTS_WIZARD", value)
    assert experimental_blueprints_wizard_enabled() is expected


def test_experimental_blueprints_wizard_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LENSES_EXPERIMENTAL_BLUEPRINTS_WIZARD", raising=False)
    assert experimental_blueprints_wizard_enabled() is True
