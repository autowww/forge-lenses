# Forge Lenses Studio UX remediation PDCA — master sequence

Composer **2.5** implements repo phases **S00–S12** for all **48** Studio UX backlog items (**FLS-001…048**) from the Playwright crawl and [lenses-studio-ux-backlog-roadmap](https://github.com/autowww/forge-lenses) canvas.

Prerequisite: Lenses Studio shell on `:8080` (`lenses-enterprise` + `lenses/serve.py`).

Executor model: **Composer 2.5** (standard variant, not `-fast`).

| Phase | Prompt | FLS IDs | Scope |
|-------|--------|---------|-------|
| S00 | [S00-scaffold.md](S00-scaffold.md) | — | SEQUENCE, gate scripts, master sequence (all 48 IDs listed below) |
| S01 | [S01-boot-resilience.md](S01-boot-resilience.md) | 031, 032 | Splash progress stages + workspace-state timeout/resilience |
| S02 | [S02-human-language.md](S02-human-language.md) | 001, 002, 003, 004 | Plain-language nav, glossary, ban path tokens, human errors |
| S03 | [S03-inspect-labs.md](S03-inspect-labs.md) | 023, 025, 029, 030 | Inspect role gate, advanced framing, Labs menu, remove demo traces |
| S04 | [S04-trust-ai-setup.md](S04-trust-ai-setup.md) | 037, 005 | AI Setup trust banner + role-clear settings labels |
| S05 | [S05-first-value-scope.md](S05-first-value-scope.md) | 016, 017, 018 | First-run wizard, friendly scope selects, release checklist picker |
| S06 | [S06-project-maturity.md](S06-project-maturity.md) | 008, 009, 010 | Project health tiers, suggested next step, this-week narrative |
| S07 | [S07-docs-readiness-home.md](S07-docs-readiness-home.md) | 011, 014 | Home attention strip + documentation review summary |
| S08 | [S08-work-depth.md](S08-work-depth.md) | 012, 013, 022 | Matrix milestone titles, freshness chips, timeline scope memory |
| S09 | [S09-guided-journeys.md](S09-guided-journeys.md) | 019, 020, 021, 048 | Tour, Monday checklist, agentic start-here, knowledge empty guidance |
| S10 | [S10-enterprise-ia.md](S10-enterprise-ia.md) | 006, 007, 024, 026, 028, 033, 034, 036, 038, 039, 040, 041, 043, 044, 046 | Enterprise IA, evidence naming, Foundry demotion, shell polish |
| S11 | [S11-narrative-polish.md](S11-narrative-polish.md) | 015, 027, 035, 042, 045, 047 | Autonomy narrative, PageHeader consistency, Publish/identity polish |
| S12 | [S12-closeout.md](S12-closeout.md) | — | Playwright crawl v2, backlog v2 canvas, full gate closeout |

## Full backlog registry (FLS-001…048)

| ID | Phase | Title |
|----|-------|-------|
| FLS-001 | S02 | Plain-language nav rename pack (WBS, Docs health, Agentic bridge, …) |
| FLS-002 | S02 | Inline glossary on first use (Story, Backlog, Roadmap, Evidence, Readiness) |
| FLS-003 | S02 | Ban path/route tokens from user chrome (workspace-md, ogs:demo:*, :8080) |
| FLS-004 | S02 | Humanize empty/error copy (no API method strings in main column) |
| FLS-005 | S04 | Rename AI Setup / Fleet / Agent runtime for role clarity |
| FLS-006 | S10 | Unify Evidence naming (one noun: Proof / Evidence — pick one) |
| FLS-007 | S10 | Demote internal program names (Foundry / Dark Factory) behind Labs framing |
| FLS-008 | S06 | Health tier on every Projects Flow card (Ready / Watch / At risk) |
| FLS-009 | S06 | Project header: promote Suggested next step over Repository charts |
| FLS-010 | S06 | This week narrative on project dashboard (story, not commits/HEAD) |
| FLS-011 | S07 | Portfolio attention strip above Home KPI wall |
| FLS-012 | S08 | Matrix cells show milestone titles, not only N stories · M WBS |
| FLS-013 | S08 | Freshness / confidence chips on Plan and Today (plain language) |
| FLS-014 | S07 | Documentation review summary card on Home + Project (counts + next fix) |
| FLS-015 | S11 | Autonomy maturity → plain readiness story (not level/grade/score jargon) |
| FLS-016 | S05 | First-run wizard: pick project + backlog (3 steps) |
| FLS-017 | S05 | Friendly backlog titles in all scope selects (never raw paths) |
| FLS-018 | S05 | Release checklist picker (discovered releases) instead of free-text graph ids |
| FLS-019 | S09 | In-app 5-stop tour (Home → Project → Today → Evidence → Publish) |
| FLS-020 | S09 | Monday checklist on Home: attention → blockers → readiness |
| FLS-021 | S09 | Agentic bridge Start-here journey (not empty catalogs + JSON) |
| FLS-022 | S08 | Timeline remembers last scope + human labels for selects |
| FLS-023 | S03 | Hide UX insights / Agent runtime / Toolset from default gear (Labs only) |
| FLS-024 | S10 | Split Setup vs Governance vs Labs in settings menu |
| FLS-025 | S03 | Who is this for? framing on every advanced route |
| FLS-026 | S10 | Simplify Flow vs Artifacts for first sessions (or defer toggle) |
| FLS-027 | S11 | Single home for Release checklist (remove Work/Knowledge duplicate) |
| FLS-028 | S10 | Reduce Classic / Full workspace UI escapes from primary chrome |
| FLS-029 | S03 | Gate TechnicalDetails / raw JSON behind Inspect (admin) role |
| FLS-030 | S03 | Remove Trace sample story / demo orchestration from default actions |
| FLS-031 | S01 | Splash: progress stages + plain status (no snapshot / commit / ISO footer) |
| FLS-032 | S01 | Workspace-state resilience: progressive shell + timeout + retry UX |
| FLS-033 | S10 | Extend ExecutiveSummaryStrip beyond Home |
| FLS-034 | S10 | Soften matrix/table density (sticky headers, empty illustrations) |
| FLS-035 | S11 | Consistent PageHeader on Boards / sparse hubs |
| FLS-036 | S10 | Ban internal status tokens from chips (scan_only, local_fixture, feature_disabled) |
| FLS-037 | S04 | AI Setup trust banner: keys stay local; nothing sent until Ask |
| FLS-038 | S10 | Fleet: When Studio uses this runner (Docs review example) |
| FLS-039 | S10 | Copilot sources panel expanded by default on Ask |
| FLS-040 | S10 | Agent runtime: Automatic vs Needs approval summary card |
| FLS-041 | S10 | Risks → concrete next pages (not only charts/evidence) |
| FLS-042 | S11 | Publish tab: human site health, not badge-only count |
| FLS-043 | S10 | Boards card face: owner + last updated without expand |
| FLS-044 | S10 | Collapse All workspace entries directory into Advanced reporting |
| FLS-045 | S11 | Milestones show business outcome field when present |
| FLS-046 | S10 | Signed-in / workspace identity without absolute filesystem path in breadcrumb |
| FLS-047 | S11 | Not signed in → guided local identity (without blocking scan) |
| FLS-048 | S09 | Knowledge empty states: sample cards + how to populate (no SQLite/API) |

Gate runner: `scripts/fl-studio-ux-pdca/check-phase-gate.sh <S00|…|S12|all>`

Do not open **S0N+1** until `./scripts/fl-studio-ux-pdca/check-phase-gate.sh S0N` is green.
