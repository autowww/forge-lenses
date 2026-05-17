#!/usr/bin/env python3
"""Docs readiness rollup (signals only — run after ``scripts/check-docs.sh``).

Produces ``build/docs-readiness.json`` + Markdown summary with weighted buckets.
Fails when the composite drops below ``--fail-under``.

Navigation/page UX budgets (`scripts/check-docs-nav-budget.py`,
``scripts/check-docs-page-budget.py``) intentionally run earlier inside ``check-docs.sh`` so this score stays focused on inventory/OpenAPI/tutorial proxies.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BUILD_DIR = REPO_ROOT / "build"

# Targets mirror the sequential gap-bridge rollout; raise over time rather than weakening CI prematurely.
_DIAGRAM_NAV_PAGE_GOAL = 18
_PUBLIC_NAV_PAGE_CEILING_GOAL = 88
_TUTORIAL_VERIFY_HIT_GOAL = 54


def _read_json(path: Path) -> dict[str, object] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _pick(inv: dict[str, object] | None, *keys: str, default: object = None) -> object:
    if not inv:
        return default
    cur: object = inv
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]  # type: ignore[index]
    return cur


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fail-under", type=float, default=88.0)
    parser.add_argument(
        "--require-live",
        action="store_true",
        help="Reserved for parity scripts (parity still manual via check-live-docs-parity.py).",
    )
    parser.add_argument(
        "--openapi-path",
        type=Path,
        default=REPO_ROOT / "docs" / "generated" / "openapi.json",
        help="Partial OpenAPI export path",
    )
    parser.add_argument(
        "--manifest-path",
        type=Path,
        default=REPO_ROOT / "lenses-docs" / "public-manifest.json",
        help="Emitted public manifest JSON",
    )
    parser.add_argument(
        "--inventory-path",
        type=Path,
        default=REPO_ROOT / "docs" / "strategy" / "documentation-inventory.json",
    )
    args = parser.parse_args()
    if args.require_live:
        print(
            "score-docs-readiness: --require-live is informational until wired to crawler output",
            file=sys.stderr,
        )

    inv = _read_json(Path(args.inventory_path))
    manifest = _read_json(Path(args.manifest_path))
    openapi_txt = ""
    openapi_path = Path(args.openapi_path)
    if openapi_path.is_file():
        openapi_txt = openapi_path.read_text(encoding="utf-8")

    schemas = float(_pick(inv, "schema_file_count", default=0) or 0)
    samples = float(_pick(inv, "sample_json_example_count", default=0) or 0)
    diagram_hits = float(_pick(inv, "diagram_public_page_hits_approx", default=0) or 0)
    pub_nav = float(_pick(inv, "effective_public_nav_page_count", default=0) or 0)
    verify_hits = float(_pick(inv, "tutorial_signal_hits_approx", "verify_hits", default=0) or 0)

    buckets: dict[str, float] = {
        "schemas": 100.0 * _clamp01(schemas / 14.0),
        "samples": 100.0 * _clamp01(samples / 14.0),
        "diagrams": 100.0 * _clamp01(diagram_hits / float(_DIAGRAM_NAV_PAGE_GOAL)),
        "effective_public_nav": 100.0 * _clamp01(pub_nav / float(_PUBLIC_NAV_PAGE_CEILING_GOAL)),
        "tutorial_verification_signal": 100.0 * _clamp01(verify_hits / float(_TUTORIAL_VERIFY_HIT_GOAL)),
        "openapi_stub": 100.0 if openapi_txt.strip() else 40.0,
        "manifest": 100.0 if manifest else 55.0,
    }

    weights = {
        "schemas": 0.18,
        "samples": 0.17,
        "diagrams": 0.17,
        "effective_public_nav": 0.12,
        "tutorial_verification_signal": 0.12,
        "openapi_stub": 0.13,
        "manifest": 0.11,
    }

    overall = sum(buckets[name] * weights[name] for name in weights)

    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    report = {
        "generated_at": stamp,
        "overall": math.floor(overall * 10) / 10,
        "buckets": {k: round(v, 1) for k, v in buckets.items()},
        "weights": weights,
        "signals": {
            "schema_file_count": int(schemas),
            "sample_json_example_count": int(samples),
            "diagram_public_page_hits_approx": int(diagram_hits),
            "effective_public_nav_page_count": int(pub_nav),
            "tutorial_verify_hits_approx": int(verify_hits),
            "diagram_nav_page_goal": _DIAGRAM_NAV_PAGE_GOAL,
            "tutorial_verify_hit_goal": _TUTORIAL_VERIFY_HIT_GOAL,
            "manifest_present": bool(manifest),
            "openapi_stub_bytes": len(openapi_txt.encode("utf-8")),
            "openapi_path": str(openapi_path.relative_to(REPO_ROOT)),
        },
    }
    json_path = BUILD_DIR / "docs-readiness.json"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    md_lines = [
        "# Docs readiness",
        "",
        f"- Generated: `{stamp}`",
        f"- Composite: **{report['overall']:.1f} / 100**",
        "",
        "## Buckets",
        "",
        "| Bucket | Score |",
        "| ------ | ----- |",
    ]
    for name, score in buckets.items():
        md_lines.append(f"| {name} | {score:.1f} |")

    md_lines.extend(
        [
            "",
            "## Signals",
            "",
            "```json",
            json.dumps(report["signals"], indent=2),
            "```",
        ]
    )

    md_path = BUILD_DIR / "docs-readiness.md"
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"score-docs-readiness: wrote {json_path.relative_to(REPO_ROOT)} (+ Markdown)")
    print(f"score-docs-readiness: composite {overall:.1f}")

    if overall + 1e-6 < float(args.fail_under):
        print(
            f"score-docs-readiness: FAIL composite {overall:.1f} < {args.fail_under}",
            file=sys.stderr,
        )
        return 1
    print("score-docs-readiness: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
