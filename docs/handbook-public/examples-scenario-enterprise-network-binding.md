---

nav_title: Scenario — Enterprise network binding
public_publish: true
audience: public
product_area: lenses
learning_level: '201'
section: builders
description: Loopback-safe binding exercise before widening Lenses listeners.
status: shipped
tier: builder
handbook_area: builders
page_type: topic
---

# Scenario — Enterprise network binding checklist

## Scenario summary

An operator verifies default loopback binds, inventories open ports, and only then widens `LENSES_HOST`/`--bind-all-interfaces`, pairing changes with firewall posture.

## User role

Platform operator or security reviewer.

## Starting state

- Forge Lenses installed per [Install and run](02-install-and-run.md).
- Shell access to `ss` or `lsof` on the host.

## Steps

1. Record `ss -lptn` while Lenses is stopped and while running on the default port.
2. Compare results with [Enterprise — network binding](enterprise-network-binding.md).
3. If widening binds, document the reverse proxy + TLS termination owner.

## Example input

```bash
ss -lptn 'sport = :8080'
```

## Example output or expected state

Only loopback (`127.0.0.1`) listeners until `--bind-all-interfaces` + proxy plan is logged.

## Verification

- Matches the Verify table inside [Enterprise — network binding](enterprise-network-binding.md).
- Alerts fire if unintended `0.0.0.0` listeners appear before allowlists tighten.

## Failure / recovery

- Roll back to loopback binds, revert env flags referencing [Configuration reference](../reference/config-env.md), rerun [Builders — auth and safety](builders-auth-and-safety.md).

## Related API/schema docs

REST narrative: [Schemas and API for builders](16-schemas-and-api-for-builders.md). JSON stub: [`sample-oauth-oidc-endpoint.json`](../examples/sample-oauth-oidc-endpoint.json) anchors OIDC appendix references.
