# U01 — Multi-repo E2E fixture + crawl v4 CI gate

**Executor:** Composer 2.5

**Backlog:** FLS3-004

## Plan

CI runs human-copy oracle and Studio UX crawl against a deterministic multi-repo workspace fixture, not only the single-repo e2e tree.

## Do

1. Add [`tests/fixtures/e2e_multi_repo/`](../../../tests/fixtures/e2e_multi_repo/) — two git repos with minimal `docs/requirements/WBS.md` + `docs/ROADMAP.md`.
2. Extend [`lenses-enterprise/scripts/e2e-lenses-with-fixture.sh`](../../../lenses-enterprise/scripts/e2e-lenses-with-fixture.sh) to seed the multi-repo tree; optional `E2E_WORKSPACE_ROOT` override.
3. Add [`workbench/studio-ux-crawl-v4.mjs`](../../../workbench/studio-ux-crawl-v4.mjs) (copy v3; assert non-sparse `/plan/matrix` on multi-repo fixture).
4. Add [`scripts/studio-ux-crawl-gate.sh`](../../../scripts/studio-ux-crawl-gate.sh) — start fixture server, run crawl, `jq` assert `splashCleared` and empty `jargonRoutes`.
5. Wire CI in [`.github/workflows/ci.yml`](../../../.github/workflows/ci.yml) — reference `studio-ux-crawl-gate` (port 17555 or documented fixture port).

## Check

```bash
scripts/fl-studio-ux3-pdca/check-phase-gate.sh U01
./scripts/studio-ux-crawl-gate.sh
```

## Act

Fix fixture seeding, crawl script, or CI job until U01 gate is green; then proceed to U02.
