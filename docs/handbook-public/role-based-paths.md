---

nav_title: Pick your path
audience: public
section: product
learning_level: overview
product_area: lenses
tier: product
handbook_area: product
status: shipped
public_publish: true
description: Role-specific reading order for Forge Lenses—recommended first pages, FAQs, and topics to postpone until fundamentals are solid.
page_type: landing
---

# Pick your path

Use this page to **shortcut to the documentation that matters for your hat** — evaluator, builder, operator, security, or facilitator. Links below resolve to handbook pages emitted for the lenses.forgesdlc.com public navigation profile without detouring into contributor-only drafts.

```blueprint-diagram
key: swimlane
alt: Readers choose Studio flows, Wizard lab, enterprise hardening, or HTTP builders after fundamentals
title: Role-based handbook branching
summary: Readers branch by role objective to reach the right handbook pages without detouring through contributor-only drafts.
node: Process flow
detail: Reader identifies which hat they wear before choosing documentation.
more: This page shortcuts to handbook pages that matter for evaluator, builder, operator, security, or facilitator roles.
node: Lane A
detail: The evaluator or builder lane for fundamentals-first reading.
more: Evaluators start with overview and install; solo developers open workspace setup and Studio 101.
node: handoff
detail: Moves from role selection to the recommended first pages.
more: Each role row in the table maps to three prioritized handbook destinations without contributor-only detours.
node: shared outcome
detail: Reader reaches governed, role-appropriate documentation quickly.
more: Links resolve to public navigation profile pages on lenses.forgesdlc.com.
node: Lane B
detail: The operator or facilitator lane for inspect-and-adapt loops.
more: Team leads, platform operators, and security reviewers follow day-two and enterprise paths.
node: inspect / adapt
detail: Reader probes live workspace behavior and adjusts the reading order.
more: Operators inspect network binding and configuration; security reviewers trace what leaves the machine.
node: feedback
detail: Outcomes inform whether to deepen or postpone advanced topics.
more: The "do not start here yet" section gates Wizard 301 and raw API catalogs until fundamentals stick.
caption: Branch by role objective after workspace setup (evaluator/builder/operator lanes)
fallback_ascii: |
  Process flow

  Lane A ──► handoff ──► shared outcome
  Lane B ──► inspect / adapt ──► feedback
```

## Role → recommended first reads

| Role | Page 1 | Page 2 | Page 3 |
|------|---------|--------|--------|
| **Evaluator** | [Lenses overview](01-lenses-overview.md) | [Install and run](02-install-and-run.md) | [Security and local-first](17-security-and-local-first.md) |
| **Solo developer** | [Workspace setup](03-workspace-setup.md) | [Studio 101](05-studio-101.md) | [Docs Health](15-docs-health.md) |
| **Team lead / coach** | [Tutorials — 201](tutorials-201.md) | [Wizard 201](10-wizard-201.md) | [Examples hub](19-examples-hub.md) |
| **Platform operator** | [Enterprise hub](enterprise-index.md) | [Enterprise network binding](enterprise-network-binding.md) | [Configuration reference](../reference/config-env.md) |
| **Security reviewer** | [Security and local-first](17-security-and-local-first.md) | [OIDC sessions](enterprise-oidc-sessions.md) | [LLM boundaries](enterprise-llm-boundaries.md) |
| **Builder / integrator** | [Builders overview](builders-api-overview.md) | [Schemas and API (builders)](16-schemas-and-api-for-builders.md) | [HTTP API route catalog](../generated/api-routes.md) |

## Role → frequent questions → answers here

| If you wonder… | Read |
|----------------|------|
| *What are Classic vs Studio vs Wizard?* | [Lenses overview](01-lenses-overview.md) |
| *How fast can I pilot this?* | [Home](../index.md) time horizons plus [Install and run](02-install-and-run.md) |
| *What leaves my machine when I enable X?* | [Security](17-security-and-local-first.md), [Fleet integration](enterprise-fleet-integration.md), [LLM setup](13-llm-and-ai-setup.md) |
| *How risky is exposing the dashboard on LAN?* | [Enterprise network binding](enterprise-network-binding.md) |
| *Which HTTP payloads are contractual?* | [Builders overview](builders-api-overview.md), [builders stability policy](builders-stability-policy.md) |
| *How do Forge SDLC, Blueprints, and this site relate?* | [Cross-site map](cross-site-map.md) |

## Tutorial ladder & hubs

- **Fundamentals**: [101 overview](tutorials-101.md) — first Classic/Studio dashboards, first Docs Health probe, Wizard 101 (**experimental** Wizard labelling applies).
- **Day-two**: [201 overview](tutorials-201.md) — repeatable Studio loops, richer Wizard facilitation, Cursor launch-pack flow.
- **Advanced / rollout**: [301 overview](tutorials-301.md) — bundles, refinement, Wizard review/recheck sophistication.

Supporting hubs: **[Enterprise hub](enterprise-index.md)**, **[Builders overview](builders-api-overview.md)**, **[Troubleshooting](12-troubleshooting.md)**.

## Do **not** start here (yet)

Reserve these until installs work and terminology from [Lenses overview](01-lenses-overview.md) sticks:

| Page | Reason |
|------|--------|
| [Tutorials — 301](tutorials-301.md) topics | Assume stable workspace + familiarity with Wizard/Studio nomenclature. |
| Heavy **Wizard 301** facilitation | Understand trust boundaries (**[wizard operator boundaries](wizard-operator-trust-boundaries.md)**) first. |
| Raw **HTTP API route catalog** | Skim **[Builders overview](builders-api-overview.md)** earlier for stability tiers. |

## Related

| Topic | Destination |
|-------|-------------|
| Full ecosystem links | [Cross-site map](cross-site-map.md) |
| KS diagram primitives | [Diagram catalog](diagram-catalog-lenses.md) |
| First broken link / port issue | [Troubleshooting](12-troubleshooting.md) |
| Releases | [Release notes](24-release-notes.md) |
