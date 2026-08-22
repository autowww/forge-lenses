#!/usr/bin/env python3
"""Fill missing YAML frontmatter on ``docs/nav.yml`` Markdown paths."""

from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError as e:
    print("enrich-docs-nav-frontmatter: install PyYAML", file=sys.stderr)
    raise SystemExit(2) from e

REPO_ROOT = Path(__file__).resolve().parents[1]
_NAV_YML = REPO_ROOT / "docs" / "nav.yml"

_SECTION_META: dict[str, tuple[str, str, str]] = {
    "start": ("start", "start", "lenses"),
    "tutorials-101": ("tutorial", "tutorials-101", "lenses"),
    "tutorials-201": ("tutorial", "tutorials-201", "lenses"),
    "tutorials-301": ("tutorial", "tutorials-301", "lenses"),
    "product-areas": ("product", "product-areas", "lenses"),
    "enterprise": ("enterprise", "enterprise", "lenses"),
    "builders": ("builder", "builders", "lenses"),
    "troubleshooting": ("troubleshooting", "troubleshooting", "lenses"),
    "resources": ("resource", "resources", "lenses"),
}

_LEARNING_BY_SECTION = {
    "tutorials-101": "101",
    "tutorials-201": "201",
    "tutorials-301": "301",
}


def _nav_sources() -> list[tuple[str, str, str]]:
    raw = yaml.safe_load(_NAV_YML.read_text(encoding="utf-8"))
    out: list[tuple[str, str, str]] = []
    for sec in raw.get("sections", []):
        sid = str(sec.get("id", "")).strip()
        for ent in sec.get("entries", []) or []:
            if isinstance(ent, str):
                path = ent.replace("\\", "/")
                nav_title_hint = ""
            else:
                path = str(ent.get("path") or ent.get("source") or "").replace("\\", "/")
                nav_title_hint = str(ent.get("nav_title") or "").strip()
            if path.endswith(".md"):
                out.append((path, sid, nav_title_hint))
    return out


def _infer_title(blob: str) -> str:
    m = re.search(r"^#\s+(.+)$", blob, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return "Forge Lenses documentation"


def _needs(val: object) -> bool:
    return val is None or str(val).strip() == ""


def _patch(text: str, section_id: str, nav_yaml_title: str) -> tuple[str, bool]:
    if not text.startswith("---"):
        return text, False
    m = re.match(r"^(---\n.*?\n)(---\n)", text, re.DOTALL)
    if not m:
        return text, False
    inner = m.group(1)[4:]
    fm = yaml.safe_load(inner) if inner.strip() else {}
    if not isinstance(fm, dict):
        fm = {}
    tier_h, handbook_h, product_h = _SECTION_META.get(
        section_id, ("tutorial", section_id.replace("-", "_"), "lenses")
    )

    dirty = False
    if _needs(fm.get("tier")):
        fm["tier"] = tier_h
        dirty = True
    if _needs(fm.get("handbook_area")):
        fm["handbook_area"] = handbook_h
        dirty = True
    if _needs(fm.get("product_area")):
        fm["product_area"] = product_h
        dirty = True
    lk = fm.get("learning_level", "").strip()
    if section_id in _LEARNING_BY_SECTION and (_needs(lk) or lk == "overview"):
        fm["learning_level"] = _LEARNING_BY_SECTION[section_id]
        dirty = True
    if _needs(fm.get("public_publish")):
        fm["public_publish"] = True
        dirty = True
    if _needs(fm.get("nav_title")):
        fm["nav_title"] = (nav_yaml_title or _infer_title(text))[:140]
        dirty = True
    if _needs(fm.get("description")):
        topic = fm.get("nav_title") or nav_yaml_title or _infer_title(text)
        fm["description"] = f"{topic} — Forge Lenses handbook entry ({section_id})."
        dirty = True
    if _needs(fm.get("status")):
        fm["status"] = "shipped"
        dirty = True

    if not dirty:
        return text, False

    head = "---\n" + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True).strip() + "\n---\n"
    return head + text[m.end() :], True


def main() -> int:
    n = 0
    for rel, sec_id, nav_title_hint in _nav_sources():
        path = REPO_ROOT / rel
        if not path.is_file():
            print(f"[skip missing] {rel}", file=sys.stderr)
            continue
        raw = path.read_text(encoding="utf-8")
        new_raw, touched = _patch(raw, sec_id, nav_title_hint)
        if touched:
            path.write_text(new_raw, encoding="utf-8")
            n += 1
    print(f"enrich-docs-nav-frontmatter: updated {n} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
