# Seeded showcase workspace (orchestration story)

Use a dedicated workspace directory (or your mono-repo root) and enable demo fixtures so Plan, Today, connectors, and copilot show a **single coherent narrative** (strategy → delivery → quality → release → ops).

## One-shot environment (bash)

From the workspace root that contains your product repos as git children:

```bash
export LENSES_EXPERIMENTAL_ORCHESTRATION_GRAPH=1
export LENSES_ORCHESTRATION_GRAPH_SEED_DEMO=1
export LENSES_DELIVERY_SIGNALS_SEED_DEMO=1
export LENSES_REPO_WORKFLOW_SEED_DEMO=1
export LENSES_CICD_ORCHESTRATION_SEED_DEMO=1
export LENSES_TEST_QUALITY_SEED_DEMO=1
export LENSES_DEVSECOPS_COMPLIANCE_SEED_DEMO=1
export LENSES_CROSS_TEAM_RELEASE_SEED_DEMO=1
export LENSES_OPS_DELIVERY_SEED_DEMO=1
export LENSES_SEARCH_REINDEX_ON_START=1
python3 -m lenses
```

Then open **http://127.0.0.1:8080/studio/plan** — use **Load demo comparison** in the portfolio panel, open **Today** for delivery cards, **Governance → Connector health** for integration status, and **SDLC copilot** on Chat or Plan.

## RBAC demo

After first GitHub PAT sign-in, `.lenses-local/lenses-access.json` is bootstrapped. Add members and optional `scopes` arrays; super admins can read **`GET /api/governance/audit`**.

## Fixture map

Canonical JSON lives under **`lenses/fixtures/`** (`orchestration-graph.demo.json`, `cicd-orchestration.demo.json`, etc.). See **`lenses/fixtures/showcase-workspace/README.md`** for a field checklist.
