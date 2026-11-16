---

nav_title: Scenario examples
public_publish: true
audience: public
product_area: lenses
learning_level: overview
section: builders
description: Narrative pointers into tutorials that mirror common enterprise scenarios.
status: shipped
tier: builder
handbook_area: builders
page_type: landing
---

# Scenario examples (by outcome)

These pages avoid duplicating canonical tutorials — each row links to the **happy path** chapter plus JSON fixtures where applicable.

| Scenario | Canonical tutorial | Machine-readable fixtures |
|----------|-------------------|---------------------------|
| [Sibling repos under one workspace root](examples-scenario-sibling-repos.md) | [Workspace setup — layouts](03-workspace-setup_01-layouts.md) | — |
| [Standalone clone vs submodule layout](examples-scenario-root-choice.md) | [Workspace setup — root choice](03-workspace-setup_02-root-choice.md) | — |
| [Daily Classic + Studio visibility](examples-scenario-classic-studio-daily.md) | [Studio 201](06-studio-201.md) | — |
| [Wizard mission — greenfield idea](examples-scenario-wizard-greenfield.md) | [Wizard 201 — start from idea](10-wizard-201_01-start-from-idea.md) | [`sample-wizard-session.json`](../examples/sample-wizard-session.json) |
| [Wizard mission — repair stage](examples-scenario-wizard-repair.md) | [Wizard 201 — repair stage](10-wizard-201_04-repair-stage.md) | above |
| [Cursor Launch Pack export](examples-scenario-cursor-launch-pack.md) | [Cursor Launch Pack](11-wizard-301_04-cursor-launch-pack.md) | [`sample-cursor-launch-pack-manifest.json`](../examples/sample-cursor-launch-pack-manifest.json) |
| [Docs Health remediation](examples-scenario-docs-health.md) | [Docs Health](15-docs-health.md) | — |
| [Local-first LLM / Ollama path](examples-scenario-llm-local.md) | [LLM and AI setup](13-llm-and-ai-setup.md) | — |
| [Enterprise network binding drill](examples-scenario-enterprise-network-binding.md) | [Enterprise — network binding](enterprise-network-binding.md) | — |
| [OIDC rehearsal](examples-scenario-oidc-login.md) | [Enterprise — OIDC sessions](enterprise-oidc-sessions.md) | [`sample-oauth-oidc-endpoint.json`](../examples/sample-oauth-oidc-endpoint.json) |
| [Live deploy parity](examples-scenario-live-deploy-parity.md) | [Docs versioning](25-docs-versioning.md) | — |
| [API workspace scan rehearsal](examples-scenario-api-workspace-scan.md) | [Schemas and API (builders)](16-schemas-and-api-for-builders.md) | — |
| [Docs inventory refresh cadence](examples-scenario-docs-inventory-refresh.md) | [Release notes](24-release-notes.md) | [`documentation-inventory.json`](../strategy/documentation-inventory.json) |
| [HTTP error envelopes for builders](examples-scenario-api-error-shape.md) | [Schemas and API (builders)](16-schemas-and-api-for-builders.md) | [`sample-api-error.json`](../examples/sample-api-error.json) |

Central JSON hub: **[JSON examples](19-examples-hub.md)** — validates against **`tests/test_docs_schemas.py`**.
