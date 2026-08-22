---

nav_title: Builders — auth and safety
public_publish: true
audience: public
product_area: lenses
learning_level: reference
section: builders
description: Bearer tokens, CORS, and local-first expectations for API automation.
status: shipped
tier: builder
handbook_area: builders
page_type: topic
---

# Builders — auth and safety

## What it is

**Lenses is local-first**: most installs bind to loopback. **`/api/auth/*`**, admin surfaces, and optional **OIDC** flows exist for hardened deployments — treat tokens like production secrets ([Security and local-first](17-security-and-local-first.md)).

## Practices

- Prefer **`GET`** for health and read-only probes; never publish **`POST`** examples with live payloads containing PII.
- If browser automation hits Lenses, keep **same-origin** fetches — follow [Studio troubleshooting](studio-troubleshooting.md) when origins diverge.
- Wizard **assist** routes may forward content to **LLM** gateways — read [Wizard operator trust boundaries](wizard-operator-trust-boundaries.md).

## Verify

Your integration docs state **where** the bearer or session cookie lives and that **CI** uses synthetic hosts only.

## What to do next

- [Configuration reference](../reference/config-env.md)
