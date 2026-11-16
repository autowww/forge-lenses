#!/usr/bin/env python3
"""Regenerate ``docs/strategy/documentation-inventory.json`` from repo state.

Run from the forge-lenses repo root:

    python3 generator/export-docs-inventory.py

Requires PyYAML. Uses embedded kitchensink ``forge-autodoc`` for nav + slug rules.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
KS_ROOT = REPO_ROOT / "kitchensink"
FORGE_AUTODOC = KS_ROOT / "forge-autodoc"
_GEN = REPO_ROOT / "generator"

for p in (str(FORGE_AUTODOC), str(_GEN)):
    if p not in sys.path:
        sys.path.insert(0, p)

import yaml  # noqa: E402

from collect_lenses_api_routes import ApiRouteSig, collect_api_route_signatures  # noqa: E402
from forge_autodoc.files import (  # noqa: E402
    slug_from_lens_repo_handbook_md,
    split_yaml_frontmatter,
)
from forge_autodoc.nav_manifest import load_lens_nav_manifest  # noqa: E402


def _api_routes_fingerprint() -> dict[str, object]:
    sigs = collect_api_route_signatures()
    joined = "\n".join(f"{s.method} {s.signature}" for s in sigs)
    digest = hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]
    return {"count": len(sigs), "sha256_prefix": digest, "methods": sorted({s.method for s in sigs})}


def _api_route_family_key(sig: ApiRouteSig) -> str:
    s = sig.signature
    if s.startswith("PREFIX:"):
        rest = s[7:].rstrip("/")
        parts = [p for p in rest.split("/") if p]
        if len(parts) >= 2:
            return f"/{parts[0]}/{parts[1]}"
        return rest or "PREFIX"
    path = s.split("?", 1)[0].strip()
    parts = [p for p in path.split("/") if p]
    if len(parts) >= 2:
        return f"/{parts[0]}/{parts[1]}"
    return path or "/"


def _api_route_families() -> dict[str, dict[str, int]]:
    by_family: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for sig in collect_api_route_signatures():
        fam = _api_route_family_key(sig)
        by_family[fam][sig.method] += 1
    return {k: dict(v) for k, v in sorted(by_family.items())}


def _enrich_page_metrics(rel: str, md_path: Path) -> dict[str, object] | None:
    if "/handbook-public/" not in rel.replace("\\", "/"):
        return None
    text = md_path.read_text(encoding="utf-8")
    fm, body = split_yaml_frontmatter(text)
    lower = body.lower()
    wc = len(body.split())
    has_verify = bool(
        re.search(r"^##\s+verify\b", lower, re.MULTILINE)
        or "| **verify**" in lower
        or "**verify**" in lower
        or "## time and checks" in lower
        or "| **check**" in lower
    )
    has_recover = bool(
        re.search(r"^##\s+recover\b", lower, re.MULTILINE)
        or "| **recover**" in lower
        or "**recover**" in lower
    )
    has_scenario = bool(
        re.search(r"^##\s+scenario\b", lower, re.MULTILINE)
        or "| **scenario**" in lower
        or "## example" in lower
    )
    has_outcome = bool(re.search(r"^##\s+outcome\b", lower, re.MULTILINE))
    code_blocks = lower.count("```")
    has_commands = "```bash" in lower or "```sh" in lower
    has_blueprint_diagram = "```blueprint-diagram" in lower
    mentions_sample_json = "sample-" in lower and ".json" in lower
    return {
        "word_count_approx": wc,
        "has_outcome_heading": has_outcome,
        "has_verify_or_checks": has_verify,
        "has_recover": has_recover,
        "has_scenario_or_example": has_scenario,
        "has_shell_commands": has_commands,
        "fenced_block_count_approx": code_blocks // 2,
        "has_blueprint_diagram_fence": has_blueprint_diagram,
        "mentions_sample_json": mentions_sample_json,
    }


def _nav_inventory() -> tuple[list[dict[str, object]], int]:
    nav_path = REPO_ROOT / "docs" / "nav.yml"
    manifest = load_lens_nav_manifest(nav_path)
    entries: list[dict[str, object]] = []
    for sec in manifest.sections:
        for ent in sec.entries:
            rel = ent.path.replace("\\", "/")
            md_path = REPO_ROOT / rel
            fm: dict[str, str] = {}
            if md_path.is_file():
                text = md_path.read_text(encoding="utf-8")
                fm, _ = split_yaml_frontmatter(text)
            slug = slug_from_lens_repo_handbook_md(md_path, REPO_ROOT) if md_path.is_file() else ""
            row: dict[str, object] = {
                "path": rel,
                "section_id": sec.id,
                "section_title": sec.title,
                "nav_title_override": ent.nav_title,
                "html_slug": slug,
                "frontmatter_keys": sorted(fm.keys()),
                "audience": fm.get("audience", "").strip() or None,
                "section_frontmatter": fm.get("section", "").strip() or None,
                "public_publish": fm.get("public_publish", "").strip() or None,
            }
            if md_path.is_file():
                metrics = _enrich_page_metrics(rel, md_path)
                if metrics is not None:
                    row["handbook_metrics"] = metrics
            entries.append(row)
    return entries, manifest.version


def _posix_rel(rel: str) -> str:
    return rel.replace("\\", "/")


def _public_publish_suppressed(fm: dict[str, str]) -> bool:
    v = fm.get("public_publish", "").strip().lower()
    return v in ("false", "0", "no", "off")


def _git_head() -> str:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        if proc.returncode == 0:
            return (proc.stdout or "").strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return ""


def _nav_public_signals() -> dict[str, object]:
    nav_disk = REPO_ROOT / "docs" / "nav.yml"
    manifest = load_lens_nav_manifest(nav_disk)
    nav_sha256 = hashlib.sha256(nav_disk.read_bytes()).hexdigest()
    flat = [_posix_rel(p) for p in manifest.flatten_paths()]
    suppressed: list[str] = []
    emitted: list[str] = []
    diagrams = 0
    wc_total = 0
    tutorial_signal = {"verify_hits": 0, "recover_hits": 0}
    for rel in flat:
        md_path = REPO_ROOT / rel
        if not md_path.is_file():
            continue
        text = md_path.read_text(encoding="utf-8")
        fm, body = split_yaml_frontmatter(text)
        if _public_publish_suppressed(fm):
            suppressed.append(rel)
            continue
        emitted.append(rel)
        if "```blueprint-diagram" in text:
            diagrams += 1
        lowered = body.lower()
        wc_total += len(body.split())
        if "verify" in lowered:
            tutorial_signal["verify_hits"] += 1
        if "recover" in lowered:
            tutorial_signal["recover_hits"] += 1

    schema_paths = sorted(REPO_ROOT.glob("docs/schemas/*.schema.json"))
    example_paths = sorted(REPO_ROOT.glob("docs/examples/sample-*.json"))
    routes_json = REPO_ROOT / "docs" / "generated" / "api-routes.json"
    routes_digest = ""
    if routes_json.is_file():
        routes_digest = hashlib.sha256(routes_json.read_bytes()).hexdigest()

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repo": "forge-lenses",
        "git_commit": _git_head() or None,
        "source_nav_path": "docs/nav.yml",
        "nav_sha256": nav_sha256,
        "nav_entry_count_manifest": len(flat),
        "effective_public_nav_page_count": len(emitted),
        "suppressed_nav_page_count": len(suppressed),
        "suppressed_pages": suppressed,
        "diagram_public_page_hits_approx": diagrams,
        "approx_sum_word_counts_handbook_nav": wc_total,
        "schema_file_count": len(schema_paths),
        "sample_json_example_count": len(example_paths),
        "generated_api_routes_json_sha256": routes_digest or None,
        "tutorial_signal_hits_approx": tutorial_signal,
    }


def build_inventory_document() -> dict[str, object]:
    if not KS_ROOT.is_dir():
        raise RuntimeError("kitchensink submodule missing")
    nav_entries, nav_version = _nav_inventory()
    api = _api_routes_fingerprint()
    families = _api_route_families()
    signals = _nav_public_signals()
    return {
        **signals,
        "nav_manifest_version": nav_version,
        "public_nav_page_count": len(nav_entries),
        "api_routes": api,
        "api_route_families": families,
        "nav_entries": nav_entries,
    }


def _write_api_route_families_md(
    path: Path, families: dict[str, dict[str, int]], api_meta: dict[str, object]
) -> None:
    count = api_meta.get("count", 0)
    fp = api_meta.get("sha256_prefix", "")
    lines = [
        "---",
        "audience: maintainer",
        "section: strategy",
        "nav_order: 6",
        "description: HTTP route families derived from generator/collect_lenses_api_routes.py (JSON sibling in documentation-inventory.json).",
        "---",
        "",
        "# API route families (generated)",
        "",
        f"Total signatures: **{count}** (inventory fingerprint `{fp}`).",
        "",
        "Regenerate with:",
        "",
        "```bash",
        "python3 generator/export-docs-inventory.py",
        "```",
        "",
        "Families group paths by **`/api/<segment>`** (or `PREFIX:/api/...` stem). Use for audits only — canonical behavior is `lenses/serve.py`.",
        "",
        "| Family | GET | POST | PUT |",
        "|--------|-----|------|-----|",
    ]
    for fam, methods in sorted(families.items()):
        g = methods.get("GET", 0)
        p = methods.get("POST", 0)
        u = methods.get("PUT", 0)
        lines.append(f"| `{fam}` | {g} | {p} | {u} |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "docs" / "strategy" / "documentation-inventory.json",
        help="JSON output path (default: docs/strategy/documentation-inventory.json)",
    )
    args = parser.parse_args()

    if not KS_ROOT.is_dir():
        print("[export-docs-inventory] kitchensink submodule missing", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)

    try:
        doc = build_inventory_document()
    except RuntimeError:
        print("[export-docs-inventory] kitchensink submodule missing", file=sys.stderr)
        return 1
    args.output.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    fam_md = REPO_ROOT / "docs" / "strategy" / "api-route-families.md"
    api_meta = doc["api_routes"]
    families_blob = doc["api_route_families"]
    assert isinstance(api_meta, dict)
    assert isinstance(families_blob, dict)
    _write_api_route_families_md(fam_md, families_blob, api_meta)
    nav_total = doc.get("public_nav_page_count")
    emitted_pub = doc.get("effective_public_nav_page_count")
    routes_ct = api_meta.get("count")
    family_ct = len(families_blob)
    print(
        f"[export-docs-inventory] wrote {args.output} (nav_manifest_rows={nav_total}, "
        f"effective_public={emitted_pub}, api_sigs={routes_ct}, families={family_ct}) + "
        f"{fam_md.relative_to(REPO_ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
