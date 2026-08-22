# S04 — Trust + AI Setup labels

**Executor:** Composer 2.5

**Backlog:** FLS-037, FLS-005

## Plan

AI Setup leads with trust boundary and outcome-oriented labels, not file paths and env var names.

## Do

1. Add trust banner to [`lenses-enterprise/src/components/LlmSettingsForm.tsx`](../../../lenses-enterprise/src/components/LlmSettingsForm.tsx): keys stay local; nothing sent until Ask/Copilot.
2. Rename gear-menu settings labels in `studioVisibleCopy` / `navigationConfig`: **AI Setup**, **Forge Fleet**, **Agent runtime** with role clarity (FLS-005).
3. Demote `.lenses-local/` path copy below the fold in Advanced/TechnicalDetails.

## Check

```bash
scripts/fl-studio-ux-pdca/check-phase-gate.sh S04
```

## Act

Add trust banner and settings renames until S04 gate is green; then proceed to S05.
