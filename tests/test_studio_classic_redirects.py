"""Classic HTML routes redirect to Studio (FLS3-001 U03)."""

from __future__ import annotations

import pytest

from lenses.serve import _studio_redirect_location


@pytest.mark.parametrize(
    ("classic_path", "expected_prefix"),
    [
        ("/", "/studio/"),
        ("/plan", "/studio/plan"),
        ("/timeline", "/studio/timeline"),
        ("/wbs", "/studio/wbs"),
        ("/websites", "/studio/websites"),
        ("/search", "/studio/search"),
        ("/projects", "/studio/projects"),
        ("/projects/acme", "/studio/projects/acme"),
    ],
)
def test_studio_redirect_location(classic_path: str, expected_prefix: str) -> None:
    loc = _studio_redirect_location(classic_path, "repo=alpha")
    assert loc.startswith(expected_prefix)
    assert "repo=alpha" in loc
