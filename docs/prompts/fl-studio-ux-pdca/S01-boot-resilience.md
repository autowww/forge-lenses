# S01 — Boot resilience

**Executor:** Composer 2.5

**Backlog:** FLS-031, FLS-032

## Plan

Studio boot must never hang silently on large workspaces. Splash shows human progress stages; workspace-state fetch has client and server timeouts with retry UX.

## Do

1. Add progress UI to [`lenses-enterprise/src/components/Splash.tsx`](../../../lenses-enterprise/src/components/Splash.tsx) — stage list + determinate/indeterminate progress (no git SHA / ISO footer in default chrome).
2. Add timeout + progressive shell in [`lenses-enterprise/src/context/WorkspaceContext.tsx`](../../../lenses-enterprise/src/context/WorkspaceContext.tsx) and/or [`lenses-enterprise/src/api/workspace.ts`](../../../lenses-enterprise/src/api/workspace.ts).
3. Add overall workspace-state scan timeout in [`lenses/serve.py`](../../../lenses/serve.py) for `/api/workspace-state` (or scan subsystem).
4. Wire retry from splash when timeout occurs.

## Check

```bash
scripts/fl-studio-ux-pdca/check-phase-gate.sh S01
cd lenses-enterprise && npm run build
```

## Act

Fix splash progress, timeout, or retry wiring until S01 gate is green; then proceed to S02.
