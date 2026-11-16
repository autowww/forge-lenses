# T07 — Workspace identity

**Executor:** Composer 2.5

**Backlog:** FLS2-008

## Plan

Header settings show guided local identity: workspace basename, profile cue, optional sign-in when OIDC is configured.

## Do

1. Extend [`HeaderSettingsMenu.tsx`](../../../lenses-enterprise/src/components/HeaderSettingsMenu.tsx) with `workspaceProfile` / `guidedSignIn` block (basename, not absolute path).
2. Link to Settings workspace docs; optional OIDC handoff when auth probe is present.

## Check

```bash
scripts/fl-studio-ux2-pdca/check-phase-gate.sh T07
```

## Act

Fix workspace profile or guided sign-in until T07 gate is green; then proceed to T08.
