# Showcase workspace — fixture checklist

This folder documents how to light up the **full orchestration story** for demos. Source payloads remain the existing `lenses/fixtures/*.demo.json` files; no duplicate data is stored here.

| Concern | Fixture file | Env to enable when no local JSON |
|---------|----------------|-----------------------------------|
| Orchestration graph | `orchestration-graph.demo.json` | `LENSES_ORCHESTRATION_GRAPH_SEED_DEMO=1` |
| Delivery signals | `delivery-signals.demo.json` | `LENSES_DELIVERY_SIGNALS_SEED_DEMO=1` |
| Repo / PR workflow | `repo-workflow.demo.json` | `LENSES_REPO_WORKFLOW_SEED_DEMO=1` |
| CI/CD control tower | `cicd-orchestration.demo.json` | `LENSES_CICD_ORCHESTRATION_SEED_DEMO=1` |
| Test / quality | `test-quality.demo.json` | `LENSES_TEST_QUALITY_SEED_DEMO=1` |
| DevSecOps | `devsecops-compliance.demo.json` | `LENSES_DEVSECOPS_COMPLIANCE_SEED_DEMO=1` |
| Cross-team release | `cross-team-release.demo.json` | `LENSES_CROSS_TEAM_RELEASE_SEED_DEMO=1` |
| Ops delivery | `ops-delivery.demo.json` | `LENSES_OPS_DELIVERY_SEED_DEMO=1` |

Optional: copy merged “golden” snippets into `.lenses-local/*.json` instead of env flags for repeatable offline demos.
