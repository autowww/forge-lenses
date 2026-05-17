# Tutorial heading checker vs gap-bridge ZIP acceptance

`scripts/check-handbook-tutorial-headings.py` enforces scaffolding (scenario framing, Steps, Verify, Recover or Next,
and minimum word depth) across **tutorial-shaped** handbook pages — not every Markdown file labeled “tutorial”.

## Intentional exclusions

Matches are skipped when either:

| Rule | Meaning |
|------|---------|
| `SKIP_BASENAMES` frozen set | Canonical hubs/resources such as **`tutorials-101.md`** through **`301.md`**, changelogs, glossaries,
  roadmap pages, **`01-lenses-overview.md`**, **Wizard/Studio reference chapters**, and thin HTTP appendix pages. These are **indexes or references**, not end-to-end walkthrough bodies. |
| `examples-scenario-*.md` | Scenario dossiers intentionally follow scenario templates validated elsewhere (`check-docs-examples-nav.py`). |
| `studio-*.md` pages | Operational Studio references (navigation, settings, dashboards) omit the Wizard-style §Verify ladder on purpose —
  parity lives in **`05-studio-101*.md`**, **`06-studio-201.md`**, and deeper tutorials that *are* scanned. |
| `builders-*.md` / `enterprise-*.md` | Builder playbooks emphasize contracts and rollback tables instead of scripted tutorial prose. |

## Policy for gap-bridge auditors

Treat **gap-bridge “every tutorial page” clauses** as applying to **`docs/handbook-public/*studio-*.md` leaves that intentionally contain step ladders** (`05-*`, **`06-studio-201.md`**, **`09-wizard-101.md`**, etc.).
If auditors need literal coverage everywhere, widen `SKIP_BASENAMES` only after rewriting each gated page — **do not silently expand scope** without product sign-off because Studio reference pages omit Verify blocks by design.

## Verification

Regression lives in **`bash scripts/check-docs.sh`** (`check-handbook-tutorial-headings` stage). Mention this document from release notes whenever the skip list moves.
