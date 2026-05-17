#!/usr/bin/env python3
"""Optional live parity check against lenses.forgesdlc.com (network off by default).

Without ``--allow-network``, print instructions and exit 0.

With ``--allow-network``, crawl the manifest-listed site URL and sanity-check responses.
Uses only standard library.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TIMEOUT = 25


def _fetch(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "ForgeLensesDocsParity/1"})
    with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:  # noqa: S310
        body = resp.read().decode("utf-8", errors="replace")
        return int(resp.status), body


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--allow-network",
        action="store_true",
        help="Enable HTTP GET checks against manifest site/base URL.",
    )
    ap.add_argument(
        "--manifest",
        type=Path,
        default=REPO_ROOT / "lenses-docs" / "public-manifest.json",
        help="Path to public-manifest.json (default: %(default)s)",
    )
    args = ap.parse_args()

    man = args.manifest
    if not man.is_file():
        print(
            "check-live-docs-parity: manifest missing — run offline build first.",
            file=sys.stderr,
        )
        return 0 if not args.allow_network else 1

    blob = json.loads(man.read_text(encoding="utf-8"))
    site = str(blob.get("site") or "").rstrip("/")
    if not args.allow_network:
        print(
            "check-live-docs-parity: network disabled.\n"
            "  Offline parity: scripts/check-public-build-parity.py\n"
            "  Live crawl after deploy:\n"
            "    python3 scripts/check-live-docs-parity.py --allow-network\n"
        )
        return 0

    if not site.startswith("http"):
        print("check-live-docs-parity: manifest.site invalid", file=sys.stderr)
        return 1

    nav_sha_in = blob.get("nav_sha256") or ""
    failures: list[str] = []

    home_url = f"{site}/"
    try:
        code, body = _fetch(home_url)
    except urllib.error.HTTPError as e:
        failures.append(f"home HTTP {e.code} {home_url}")
        body = ""
        code = e.code
    except OSError as e:
        failures.append(f"home fetch error {home_url}: {e}")
        return 1

    if code != 200:
        failures.append(f"home expected 200 got {code} {home_url}")
    lowered = body.lower()
    if "reference handbook (internal)" in lowered:
        failures.append("live home contains forbidden phrase reference handbook (internal)")
    if nav_sha_in:
        snippet = nav_sha_in[:24]
        if snippet not in body:
            failures.append(
                "home HTML missing expected forge-lenses nav hash fragment — "
                "deploy may lag or meta tags missing"
            )

    sections = blob.get("sections") or []
    pages = blob.get("pages") or []

    sampled: dict[str, str] = {}
    for row in pages:
        if isinstance(row, dict):
            slug = str(row.get("output_slug") or "").strip()
            sec = str(row.get("section_id") or "").strip()
            if sec and slug and sec not in sampled:
                sampled[sec] = slug

    for slug in sampled.values():
        url = f"{site}/{slug.lstrip('/')}"
        try:
            c2, body2 = _fetch(url)
            if c2 != 200:
                failures.append(f"sample GET {url} returned {c2}")
            elif nav_sha_in and nav_sha_in[:24] not in body2:
                failures.append(f"sample page missing provenance meta tags: {url}")
        except OSError as e:
            failures.append(f"fetch {url}: {e}")

    first_section_slug = ""
    if isinstance(sections, list) and sections and isinstance(pages, list):
        sid0 = str((sections[0] or {}).get("id") or "")
        if sid0:
            for row in pages:
                if isinstance(row, dict) and str(row.get("section_id")) == sid0:
                    first_section_slug = str(row.get("output_slug") or "")
                    break
    if first_section_slug:
        u = f"{site}/{first_section_slug.lstrip('/')}"
        try:
            c3, body3 = _fetch(u)
            if c3 != 200:
                failures.append(f"first-nav-section sample {u} HTTP {c3}")
        except OSError as e:
            failures.append(f"first-section sample {u}: {e}")

    if failures:
        for fmsg in failures:
            print(f"check-live-docs-parity: {fmsg}", file=sys.stderr)
        return 1
    print("check-live-docs-parity: OK (live probes succeeded)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
