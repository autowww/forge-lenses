# V00 — PDCA scaffold

**Executor:** Composer 2.5

## Plan

Confirm Forge Lenses Studio UX4 remediation PDCA harness exists: master sequence, `SEQUENCE.yaml`, gate and run scripts. No UI remediation in this phase.

## Do

1. Read [00-master-sequence.md](00-master-sequence.md) for phase order V00–V05 and FLS4-001…004 mapping.
2. Verify `scripts/fl-studio-ux4-pdca/{SEQUENCE.yaml,check-phase-gate.sh,pdca-run-phase.sh,cursor-agent-run-phase.sh}` are present.
3. Do **not** port nested roadmap React, Sites browse, bundle splits, or board redirects in this phase.

## Check

```bash
scripts/fl-studio-ux4-pdca/check-phase-gate.sh V00
```

## Act

Add or fix missing scaffold files until V00 gate is green; then proceed to V01.
