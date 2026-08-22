# Forge Lenses Studio UX5 remediation PDCA — master sequence

Composer **2.5** implements repo phases **W00–W05** for all **4** Studio UX5 backlog items (**FLS5-001…004**) from the Playwright crawl v5 canvas.

Prerequisite: **fl-studio-ux4-pdca** V00–V05 complete (crawl v5 green, FLS4-001…004 resolved).

Executor model: **Composer 2.5** (standard variant, not `-fast`).

| Phase | Prompt | FLS5 IDs | Scope |
|-------|--------|----------|-------|
| W00 | [W00-scaffold.md](W00-scaffold.md) | — | SEQUENCE, gate scripts, master sequence |
| W01 | [W01-nested-roadmap-polish.md](W01-nested-roadmap-polish.md) | 001 | Modal animations, Escape/focus, tier detail panel |
| W02 | [W02-sites-unified-chrome.md](W02-sites-unified-chrome.md) | 002 | `SitePreviewShell`; `/view/local-site` → `/websites/browse` |
| W03 | [W03-index-bundle-600kb.md](W03-index-bundle-600kb.md) | 003 | Lazy `Layout` + copilot chunk; index &lt;600 KB |
| W04 | [W04-render-classic-delete.md](W04-render-classic-delete.md) | 004 | Remove dead `page_*` builders from `render.py` |
| W05 | [W05-closeout.md](W05-closeout.md) | — | Crawl v6, backlog v6 canvas, full gate closeout |

## Full backlog registry (FLS5-001…004)

| ID | Phase | Title |
|----|-------|-------|
| FLS5-001 | W01 | Nested roadmap parity polish |
| FLS5-002 | W02 | Sites browse unified chrome |
| FLS5-003 | W03 | Index bundle &lt;600 KB |
| FLS5-004 | W04 | Delete `render.py` classic `page_*` builders |

Gate runner: `scripts/fl-studio-ux5-pdca/check-phase-gate.sh <W00|…|W05|all>`

Do not open **W0N+1** until `./scripts/fl-studio-ux5-pdca/check-phase-gate.sh W0N` is green.
