#!/usr/bin/env python3
"""Tutorial scaffolding for handbook-public pages (prompt pack §12).

Broader legacy replacement for ``check-docs-tutorial-structure.py``: scans almost every
``docs/handbook-public/*.md`` except hubs/reference stubs identified below.

Requires framing + executable structure:
- Scenario framing (prerequisites / outcome / when-to-use / what-it-is …)
- Steps (explicit heading **or** Wizard/workspace heuristics below)
- Verify synonyms (headings, tables, ``verify success by …`` prose)
- Recover **or** Next synonyms (including ``next steps:`` inline)

Skip policy rationale (versus gap-bridge wording): **`docs/maintainer/tutorial-depth-scope.md`**.

Skipped: tutorials hubs, CI canary, resources, schemas/atlas, thin scenario stubs,
Studio/Builders/Enterprise reference chapters, Wizard HTTP appendices.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HANDPUBLIC = REPO_ROOT / "docs" / "handbook-public"

SKIP_BASENAMES = frozenset(
    {
        "tutorials-101.md",
        "tutorials-201.md",
        "tutorials-301.md",
        "98-doc-ci-canary.md",
        "cross-site-map.md",
        "diagram-catalog-lenses.md",
        "role-based-paths.md",
        "20-support.md",
        "21-glossary.md",
        "22-changelog.md",
        "23-roadmap.md",
        "24-release-notes.md",
        "25-docs-versioning.md",
        "26-examples-scenarios-hub.md",
        "01-lenses-overview.md",
        "04-studio-overview.md",
        "08-wizard-overview.md",
        "14-studio-route-map.md",
        "16-schemas-and-api-for-builders.md",
        "19-examples-hub.md",
        "12-troubleshooting.md",
        "17-security-and-local-first.md",
        "03-workspace-setup.md",
        "10-wizard-201.md",
        "11-wizard-301.md",
        "wizard-builder-session-api.md",
        "wizard-operator-trust-boundaries.md",
    }
)


def _stripped_body(path: Path) -> tuple[str, int]:
    """Return lowercase body sans YAML frontmatter and fenced code blocks (+ approx word count)."""
    text = path.read_text(encoding="utf-8")
    body = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            body = parts[2]
    no_code = re.sub(r"```[^`]*```", " ", body, flags=re.DOTALL)
    wc = len(re.findall(r"\w+", no_code))
    return no_code.lower(), wc


MIN_APPROX_WORDS = 220


def _check(rel: str, b: str, approx_words: int) -> list[str]:
    errs: list[str] = []

    has_verify = bool(
        re.search(r"^##\s+verify\b", b, re.MULTILINE)
        or "## time and checks" in b
        or "| **verify**" in b
        or "| **check**" in b
        or "## how to verify" in b
        or "verify success by" in b
        or "how to verify success" in b
        or "**what to check**" in b
        or re.search(r"^##\s+example scenario\b", b, re.MULTILINE)
    )
    if not has_verify:
        errs.append(f"{rel}: missing Verify section (## Verify, ## Time and checks, or | **Verify** |)")

    has_rec_or_next = bool(
        re.search(r"^##\s+recover\b", b, re.MULTILINE)
        or re.search(r"^##\s+next\b", b, re.MULTILINE)
        or "| **recover**" in b
        or "## what to do next" in b
        or "next steps:" in b
        or "## next ladder" in b
    )
    if not has_rec_or_next:
        errs.append(f"{rel}: missing Recover or Next (## Recover, ## Next, ## What to do next, …)")

    has_scen_or_pre = bool(
        re.search(r"^##\s+scenario\b", b, re.MULTILINE)
        or re.search(r"^##\s+prerequisites\b", b, re.MULTILINE)
        or "| **scenario**" in b
        or "## when to use it" in b
        or "## when to use this" in b
        or re.search(r"^##\s+when to use\b", b, re.MULTILINE)
        or re.search(r"^##\s+outcome\b", b, re.MULTILINE)
        or re.search(r"^##\s+inputs you need\b", b, re.MULTILINE)
        or re.search(r"^##\s+step-by-step\b", b, re.MULTILINE)
        or re.search(r"^##\s+what it is\b", b, re.MULTILINE)
        or re.search(r"^##\s+who should run\b", b, re.MULTILINE)
    )
    if not has_scen_or_pre:
        errs.append(f"{rel}: missing Scenario framing (Prerequisites, Outcome, When to use it, …)")

    has_steps = bool(
        re.search(r"^##\s+steps\b", b, re.MULTILINE)
        or re.search(r"^##\s+step-by-step\b", b, re.MULTILINE)
        or re.search(r"^##\s+first session flow\b", b, re.MULTILINE)
        or re.search(r"^##\s+procedure\b", b, re.MULTILINE)
        or re.search(r"^##\s+migration checklist\b", b, re.MULTILINE)
        or (
            "## outcome" in b
            and "## example scenario" in b
            and "## inputs you need before the session" in b
        )
        or ("## worked example" in b and "## prerequisites" in b)
        or ("## configure providers" in b and "verify success by" in b)
        or ("## how to verify" in b and "/api/docs-health/" in b)
    )
    if not has_steps:
        errs.append(f"{rel}: missing Steps (## Steps, ## Step-by-step, ## First session flow, …)")

    if approx_words < MIN_APPROX_WORDS:
        errs.append(
            f"{rel}: body too shallow (~{approx_words} words, need ≥{MIN_APPROX_WORDS} outside code fences)"
        )

    return errs


def main() -> int:
    bad: list[str] = []
    for path in sorted(HANDPUBLIC.glob("*.md")):
        rel = path.relative_to(REPO_ROOT).as_posix()
        if path.name in SKIP_BASENAMES:
            continue
        if path.name.startswith("examples-scenario-"):
            continue
        if path.name.startswith("studio-") and path.name.endswith(".md"):
            continue
        if path.name.startswith("builders-") and path.name.endswith(".md"):
            continue
        if path.name.startswith("enterprise-") and path.name.endswith(".md"):
            continue
        body_lower, wc = _stripped_body(path)
        bad.extend(_check(rel, body_lower, wc))
    if bad:
        for line in bad:
            print(line, file=sys.stderr)
        print(f"check-handbook-tutorial-headings: {len(bad)} issue(s)", file=sys.stderr)
        return 1
    print("check-handbook-tutorial-headings: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
