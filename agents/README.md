# Agents (forge-lenses)

Mutable automation workspace per [`blueprints/agents/ORCHESTRATION.md`](blueprints/agents/ORCHESTRATION.md).

| Path | Purpose |
|------|---------|
| `workspaces/` | Legacy path; **new** Studio screenshot tours default to **`<workspace>/.workspace-screenshots/forge-lenses/studio-explore/`** (outside this repo). |

**Studio exploration:** from `desktop/`, run `npm run studio-explore` (requires `python3 -m lenses` on `LENSES_BASE_URL`). See [`desktop/studio-explore/README.md`](../desktop/studio-explore/README.md) and [`docs/STUDIO-EXPLORE-SNAPSHOTS.md`](../docs/STUDIO-EXPLORE-SNAPSHOTS.md).

**Full check matrix** (npm ci, tour with retries, pytest, Playwright E2E): [`scripts/run-desktop-and-explore-checks.sh`](../scripts/run-desktop-and-explore-checks.sh).
