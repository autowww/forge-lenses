# T00 — PDCA scaffold

**Executor:** Composer 2.5

## Plan

Confirm Forge Lenses Studio UX2 remediation PDCA harness exists: master sequence, `SEQUENCE.yaml`, gate and run scripts. No UI remediation in this phase.

## Do

1. Read [00-master-sequence.md](00-master-sequence.md) for phase order T00–T09 and FLS2-001…012 mapping.
2. Verify `scripts/fl-studio-ux2-pdca/{SEQUENCE.yaml,check-phase-gate.sh,pdca-run-phase.sh,cursor-agent-run-phase.sh}` are present.
3. Do **not** fix oracle spec, empty states, or timeline Gantt in this phase.

## Check

```bash
scripts/fl-studio-ux2-pdca/check-phase-gate.sh T00
```

## Act

Add or fix missing scaffold files until T00 gate is green; then proceed to T01.
