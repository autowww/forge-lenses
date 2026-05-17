"""Studio client routes (``lenses-enterprise``) vs handbook atlas coverage."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
ATLAS = ROOT / "docs" / "handbook-public" / "14-studio-route-map.md"
COVERAGE = ROOT / "docs" / "strategy" / "studio-route-doc-coverage.yaml"


def test_studio_route_atlas_covers_registered_needles() -> None:
    raw = yaml.safe_load(COVERAGE.read_text(encoding="utf-8"))
    needles = raw.get("needles") or []
    blob = ATLAS.read_text(encoding="utf-8")
    missing = [n for n in needles if str(n) not in blob]
    assert not missing, f"14-studio-route-map.md missing needles: {missing[:10]}"


def test_app_tsx_route_paths_subset_documented() -> None:
    """Every static ``path=`` segment from App.tsx (no leading colon) appears in the atlas or coverage list."""
    app_tsx = ROOT / "lenses-enterprise" / "src" / "App.tsx"
    text = app_tsx.read_text(encoding="utf-8")
    import re

    paths = re.findall(r'<Route\s+path="([^"]+)"', text)
    static_tokens: set[str] = set()
    for p in paths:
        for part in p.strip("/").split("/"):
            if not part or part.startswith(":") or part.endswith("*"):
                continue
            static_tokens.add(part)
    blob = ATLAS.read_text(encoding="utf-8")
    raw = yaml.safe_load(COVERAGE.read_text(encoding="utf-8"))
    extra_needles = set(raw.get("needles") or [])
    missing = sorted(t for t in static_tokens if t not in blob and t not in extra_needles)
    allowable_gap = {"index"}  # React Router index routes — not a path token
    missing = [m for m in missing if m not in allowable_gap]
    assert not missing, (
        "Add these Studio path tokens to 14-studio-route-map.md (table or prose) "
        f"or extend studio-route-doc-coverage.yaml: {missing}"
    )
