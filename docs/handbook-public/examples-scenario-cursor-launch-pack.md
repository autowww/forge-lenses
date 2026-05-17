---

nav_title: Scenario — Cursor launch pack
public_publish: true
audience: public
product_area: wizard
learning_level: overview
section: builders
description: Exporting editor handoff context after Review and Recheck (experimental).
status: experimental
tier: builder
handbook_area: builders
page_type: topic
---

# Scenario — Cursor Launch Pack export

## Outcome

A **Launch Pack** bundle carries prompts and file context into **Cursor** (or another editor) without executing commands on your machine by itself.

## Canonical path

[Cursor Launch Pack](11-wizard-301_04-cursor-launch-pack.md) after [Review and recheck](11-wizard-301_03-review-recheck.md).

## Fixtures

[`sample-cursor-launch-pack-manifest.json`](../examples/sample-cursor-launch-pack-manifest.json) — see [JSON examples hub](19-examples-hub.md).

## Avoid

- Exporting while **strict** mode still blocks required slices — fix the listed Wizard step first.
