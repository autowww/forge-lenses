# Apply · verify · archive — adopt-epic-execution-profile

WBS Epic **M1E3** · OpenSpec change `adopt-epic-execution-profile` · schema **forge-sdlc**

## Apply

Human: Charge approved after Lite acceptance review.

Agent / maintainer:

1. `export OPENSPEC_TELEMETRY=0`
2. Read `proposal.md`, `specs/epic-charge-profile/spec.md`, and optional `tasks.md` (non-binding).
3. Implement observable outcomes:
   - `openspec/` tree with `forge-sdlc` schema and `config.yaml` project context.
   - [`docs/maintainer/openspec-adoption.md`](../../../docs/maintainer/openspec-adoption.md) with telemetry default.
   - [`forge/charge.md`](../../../forge/charge.md) — **Active Epics** row for **M1E3** linked to this change and profile canon.
4. `openspec instructions apply --change adopt-epic-execution-profile` — confirm no blocked artifacts.

## Verify

Against Lite scenarios in `specs/epic-charge-profile/spec.md`:

| Scenario | Check |
|----------|-------|
| Charge lists Epics not Sparks | `forge/charge.md` has **Active Epics** table and dual-profile header |
| Charged Epic traces to OpenSpec | Row `#1`: id **M1E3**, change **adopt-epic-execution-profile**, status set |
| Profile canon reachable | Header links to `EPIC-EXECUTION-PROFILE.md` |

CLI validation:

```bash
cd forge-lenses
export OPENSPEC_TELEMETRY=0
openspec validate adopt-epic-execution-profile
openspec schema validate forge-sdlc
```

Phase gate (workspace):

```bash
cd /home/lzvyahin/Code
./scripts/epic-l3-openspec-pdca/check-phase-gate.sh J03
```

Assay evidence: validation output + Charge diff; no Ember Log required (no Epic-scope decision beyond documented adoption).

## Archive

After verify green and human merge/review:

```bash
cd forge-lenses
export OPENSPEC_TELEMETRY=0
openspec archive adopt-epic-execution-profile
```

Then update `forge/charge.md` — move **M1E3** from Active Epics (or mark complete) per team convention. Archive ≠ Product Spark **Released**; Assay for the Product Spark milestone remains separate.
