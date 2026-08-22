---

nav_title: Autonomy maturity in Studio
public_publish: true
audience: public
product_area: lenses
tier: practitioner
handbook_area: lenses
learning_level: '201'
section: studio-wizard
status: experimental
description: Autonomy maturity assessment in Studio — Forge Lenses handbook entry (product-areas).
---

# Autonomy maturity (Studio, experimental)

Lenses Studio can assess each workspace project against the Forge **autonomy maturity framework**: what autonomy level and grade the repo has actually *proven*, a 0–100 score, and the cheapest next promotion. The canonical scoring spec lives in Blueprints (`AUTONOMY-MATURITY-FRAMEWORK.md`); the ladder itself (levels L0–L8, grades a–d, sub-levels L1.1–L4.3) is defined in Blueprints `AUTONOMY-LEVELS.md`.

## Enabling

The panel is **off by default**, behind two flags:

| Flag | Where | Effect |
|------|-------|--------|
| `LENSES_EXPERIMENTAL_AUTONOMY_MATURITY=1` | Lenses server environment | Enables the three API endpoints (otherwise they return 404 `disabled`) |
| `VITE_EXPERIMENTAL_AUTONOMY_MATURITY=1` | Studio build environment | Registers the routes and the Knowledge → govern sidebar entry |

## Surfaces

- **`/studio/autonomy-maturity`** — workspace table: one row per git project with its observed claim (e.g. `L2.2b`), score, and top recommendation, weakest first.
- **`/studio/projects/:name/autonomy-maturity`** — one project in detail: hero score and claim, ladder position (L0–L4 band), score components with weights, gate signals, gap checklist ordered cheapest-promotion-first, and run-evidence summary.

## What is measured

Signals are **observed from the repo**, never from Wizard session intent:

1. **Gate definition (weight 40)** — `forge/forge.config.yaml` with the three assay keys, synced `.cursor/rules`, CI config, and a test suite.
2. **Demonstrated evidence (30)** — Dark Factory style machine records (`runs/**/machine/assay.json`) with a declared level or sub-level and a green assay.
3. **Repeatability (20)** — ≥5 green runs at the observed level with escalation rate below 40%.
4. **Operational metrics (10)** — escalation trend and review-sampling records (grade d territory).

A bare repo observes **L0a** with a full recommendation list; a repo with one green `L2.2` run and full gates observes **L2.2b**.

## API

| Endpoint | Payload |
|----------|---------|
| `GET /api/autonomy-maturity/enabled` | `{ ok, enabled }` |
| `GET /api/autonomy-maturity/overview` | `{ ok, projects[], count }` — weakest first |
| `GET /api/project/<name>/autonomy-maturity` | Full per-project report (claim, components, signals, recommendations) |

Project access follows the standard Lenses per-project RBAC; the overview only lists projects visible to the caller's scan.
