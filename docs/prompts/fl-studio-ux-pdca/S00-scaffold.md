# S00 — PDCA scaffold

**Executor:** Composer 2.5

## Plan

Confirm Forge Lenses Studio UX remediation PDCA harness exists: master sequence, `SEQUENCE.yaml`, gate and run scripts. No UI remediation in this phase.

## Do

1. Read [00-master-sequence.md](00-master-sequence.md) for phase order S00–S12 and FLS-001…048 mapping.
2. Verify `scripts/fl-studio-ux-pdca/{SEQUENCE.yaml,check-phase-gate.sh,pdca-run-phase.sh,cursor-agent-run-phase.sh}` are present.
3. Do **not** fix Splash, nav copy, or inspect gates in this phase.

## Check

```bash
scripts/fl-studio-ux-pdca/check-phase-gate.sh S00
```

## Act

Add or fix missing scaffold files until S00 gate is green; then proceed to S01.
