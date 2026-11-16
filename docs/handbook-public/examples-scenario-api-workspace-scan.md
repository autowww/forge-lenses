---

nav_title: Scenario — API workspace scan rehearsal
public_publish: true
audience: public
product_area: studio
learning_level: '201'
section: builders
description: Read-only traversal of `/api/repo/*` workspaces before trusting Studio overlays.
status: shipped
tier: builder
handbook_area: builders
page_type: topic
---

# Scenario — API workspace scan rehearsal

## Scenario summary

Use documented GET endpoints to list workspace roots, confirm slugs match disk layout, then graduate to Wizard or Docs Health overlays.

## User role

Integrator validating automation harnesses.

## Starting state

- Local Lenses up with repos registered in Studio.
- HTTP client restricted to localhost.

## Steps

1. Read [Schemas and API for builders](16-schemas-and-api-for-builders.md) for `/api/repo` families.
2. Issue GET-only probes mirroring CI smoke tests (`curl` snippets stay local).
3. Compare payloads with filesystem paths under `$LENSES_WORKSPACE_ROOT`.

## Example input

`curl http://127.0.0.1:8080/api/repo/status` once per handbook guidance (swap port).

## Example output or expected state

Structured JSON referencing discovered repos without surfacing PAT material.

## Verification

Responses match swagger-level descriptions in handbook tables; failures route to [Troubleshooting](12-troubleshooting.md).

## Failure / recovery

Reset `.lenses-local` caches per [Security and local-first](17-security-and-local-first.md), rescan host via [Workspace setup — scan host](03-workspace-setup_03-scan-host.md).

## Related API/schema docs

[Generated HTTP routes](generated-api-routes.html) + [`docs/generated/openapi.json`](../generated/openapi.json) (partial catalog).
