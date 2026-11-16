---

nav_title: Scenario — OIDC login rehearsal
public_publish: true
audience: public
product_area: lenses
learning_level: '201'
section: builders
description: Dry-run checklist for attaching OIDC in front of Lenses APIs.
status: shipped
tier: builder
handbook_area: builders
page_type: topic
---

# Scenario — OIDC login rehearsal

## Scenario summary

Validate issuer metadata, JWKS reachability, redirect URLs, and `/api/auth/status` parity inside the same hostname you publish to teammates.

## User role

Security engineer + operator pair.

## Starting state

- Reverse proxy hostname matches what browsers use for Studio.
- Maintainers captured OIDC env vars in [Configuration reference](../reference/config-env.md).

## Steps

1. Fetch `.well-known/openid-configuration` from the issuer.
2. Exercise login through the proxy path described in [Enterprise — OIDC sessions](enterprise-oidc-sessions.md).
3. Confirm GET-only routes still answer without session.

## Example input

Sanitized snippet of `LENSES_OIDC_ISSUER` + callback base URL (no secrets).

## Example output or expected state

Session cookie established, `/api/auth/status` shows expected subject, no redirect loops.

## Verification

Follow the Verify section in [Enterprise — OIDC sessions](enterprise-oidc-sessions.md).

## Failure / recovery

Purge cookies, disable allowlists, return to loopback-only listener, compare env matrix vs config reference.

## Related API/schema docs

[`sample-oauth-oidc-endpoint.json`](../examples/sample-oauth-oidc-endpoint.json).
