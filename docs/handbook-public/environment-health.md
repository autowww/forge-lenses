# Environment health in Lenses

Lenses aggregates per-environment health using the same envelope returned by product `/health` endpoints.

## Generic envelope

| Field | Meaning |
|-------|---------|
| `status` | `ok`, `degraded`, or `down` |
| `summary` | Rollup message |
| `environment` | `id`, `git_sha`, `lane` |
| `checks` | Product-specific array |

## API

`GET /api/deploy/environment-health?url=<gateway-health-url>&bearer=<token>`

`GET /api/deploy/pipelines?project=forge-market` lists `default` and named pipelines under `forge/pipelines/`.

## Multi-pipeline

- Legacy: `forge/delivery-pipeline.yaml` → pipeline id `default`
- Named: `forge/pipelines/<id>.yaml` (e.g. `clean.yaml` for clean-install)

Each environment may declare `health_profile.required_checks` in the pipeline descriptor.
