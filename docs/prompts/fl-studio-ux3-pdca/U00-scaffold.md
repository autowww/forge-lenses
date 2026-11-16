# U00 — PDCA scaffold

**Executor:** Composer 2.5

## Plan

Confirm Forge Lenses Studio UX3 remediation PDCA harness exists: master sequence, `SEQUENCE.yaml`, gate and run scripts. No UI remediation in this phase.

## Do

1. Read [00-master-sequence.md](00-master-sequence.md) for phase order U00–U08 and FLS3-001…006 mapping.
2. Verify `scripts/fl-studio-ux3-pdca/{SEQUENCE.yaml,check-phase-gate.sh,pdca-run-phase.sh,cursor-agent-run-phase.sh}` are present.
3. Do **not** fix Classic UI links, roadmap React, or crawl v4 in this phase.

## Check

```bash
scripts/fl-studio-ux3-pdca/check-phase-gate.sh U00
```

## Act

Add or fix missing scaffold files until U00 gate is green; then proceed to U01.
