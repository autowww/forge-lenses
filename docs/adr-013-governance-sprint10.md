# ADR-013 — Governance, OIDC foundation, and connector operations (Sprint 10)

## Status

Accepted — implemented in forge-lenses.

## Context

The product needed **enterprise-credible** access and operations: finer semantics than “read/write project”, a path to **SSO**, a **unified audit trail** for sensitive actions, **connector visibility**, and fewer **placeholder** surfaces in Plan/Studio.

## Decision

1. **RBAC scopes** — Introduced named scopes (`workspace.*`, `project.*`, `environment.read`, `release.*`, `admin.*`) in `lenses/governance/scopes.py`. Default sets are **derived from existing roles**; optional per-member **`scopes`** array in `lenses-access.json` overrides the role-derived set (validated against a fixed allowlist).
2. **Permission-aware API** — `GET /api/project/<name>/context` now returns **`scopes`** and **`scopes_source`** alongside existing flags.
3. **OIDC foundation** — Optional env-driven Authorization Code + PKCE flow: `GET /api/auth/oidc/status`, `GET /api/auth/oidc/login` (302), `GET /api/auth/oidc/callback`. Sessions record **`auth_provider`** (`github` \| `oidc`). GitHub PAT sign-in remains the default local path.
4. **Governance audit** — Append-only **`.lenses-local/governance-audit.jsonl`** with kinds: `data_change`, `approval`, `ai_action`, `connector_sync`. Wired for access member changes, search reindex start, Forgesdlc blog sync, SDLC copilot chat/commit. **`GET /api/governance/audit`** is **super_admin** only.
5. **Connector health** — **`GET /api/connectors/health`** aggregates enabled/provider/hints across delivery, repo workflow, CI/CD, quality, DevSecOps, cross-team release, and ops. When RBAC is enforced, requires session plus **super_admin** or **listed project membership**.
6. **Studio** — Routes **`/governance/connectors`** and **`/governance/audit`**; gear menu links replace doc-only dead ends. **Scenario tradeoffs** on Plan reads live **`scenario_compare`** from **`/api/orchestration/portfolio-context`** when both scenario query params are set.
7. **E2E** — Optional Playwright contract smoke: `desktop/e2e/studio-http-smoke.spec.ts` with **`LENSES_E2E=1`** (see file header).

## Consequences

- **Positive** — Operators see integration health in one place; audits centralize compliance-relevant actions; OIDC can be enabled without removing GitHub.
- **Negative** — OIDC id_token validation is minimal unless extended (signature verification, nonce); production deployments should tighten validation and use HTTPS-only redirects.
- **Follow-up** — Persist connector “last sync” timestamps per adapter; expand audit to sticker/registry writes; UI for editing `scopes` on members.
