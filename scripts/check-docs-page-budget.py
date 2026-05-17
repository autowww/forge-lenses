#!/usr/bin/env python3
"""Approximate word-count budgets per ``page_type`` (Forge Lenses handbook).

Defaults are advisory: prints warnings to stderr while exiting 0.

Environment:

- ``DOCS_PAGE_BUDGET_STRICT=1`` — exit non-zero on violations.
- ``DOCS_PAGE_BUDGET_WARN=0`` — silence warnings (still fails in strict mode).
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError as e:
    print("check-docs-page-budget: install PyYAML", file=sys.stderr)
    raise SystemExit(2) from e

REPO_ROOT = Path(__file__).resolve().parent.parent

_ALLOWED_TYPES = frozenset(
    {
        "landing",
        "hub",
        "tutorial",
        "how-to",
        "concept",
        "topic",
        "reference",
        "troubleshooting",
        "runbook",
        "internal-ci",
    }
)

# (min_words, max_words) inclusive-ish guidance — soft rails for rollout.
_BANDS: dict[str, tuple[int, int]] = {
    "landing": (140, 2200),
    "hub": (140, 2200),
    "tutorial": (260, 9000),
    "how-to": (160, 5200),
    "concept": (90, 7200),
    "topic": (60, 8200),
    "reference": (70, 12000),
    "troubleshooting": (160, 9000),
    "runbook": (180, 9000),
    "internal-ci": (0, 999999),
}


def _nav_paths() -> list[str]:
    nav = REPO_ROOT / "docs/nav.yml"
    raw = yaml.safe_load(nav.read_text(encoding="utf-8"))
    out: list[str] = []
    for sec in raw.get("sections", []):
        for ent in sec.get("entries", []) or []:
            if isinstance(ent, str):
                out.append(ent.replace("\\", "/"))
            else:
                p = ent.get("path") or ent.get("source")
                if p:
                    out.append(str(p).replace("\\", "/"))
    return out


def _frontmatter_block(text: str) -> tuple[dict[str, object] | None, str]:
    if not text.startswith("---"):
        return None, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None, text
    data = yaml.safe_load(parts[1])
    return (data if isinstance(data, dict) else None), parts[2]


def _approx_words(body: str) -> int:
    no_code = re.sub(r"```[^`]*```", " ", body, flags=re.DOTALL)
    return len(re.findall(r"\w+", no_code))


def main() -> int:
    strict = os.environ.get("DOCS_PAGE_BUDGET_STRICT", "").strip() == "1"
    warn = os.environ.get("DOCS_PAGE_BUDGET_WARN", "1").strip() != "0"

    warns: list[str] = []
    errors: list[str] = []

    for rel in sorted(set(_nav_paths())):
        path = REPO_ROOT / rel
        if not path.is_file() or not rel.endswith(".md"):
            continue
        text = path.read_text(encoding="utf-8")
        fm, body = _frontmatter_block(text)
        if not fm:
            errors.append(f"{rel}: missing YAML frontmatter")
            continue
        pt_raw = str(fm.get("page_type", "") or "").strip()
        if not pt_raw:
            errors.append(f"{rel}: missing page_type")
            continue
        if pt_raw not in _ALLOWED_TYPES:
            errors.append(f"{rel}: unknown page_type {pt_raw!r}")
            continue
        if pt_raw == "internal-ci":
            continue

        band = _BANDS.get(pt_raw)
        if not band:
            continue
        lo, hi = band
        wc = _approx_words(body)
        if wc < lo or wc > hi:
            msg = f"{rel}: page_type={pt_raw} words≈{wc} outside soft band [{lo},{hi}]"
            if strict:
                errors.append(msg)
            elif warn:
                warns.append(msg)

    for w in warns:
        print(w, file=sys.stderr)

    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        return 1

    print("check-docs-page-budget: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
