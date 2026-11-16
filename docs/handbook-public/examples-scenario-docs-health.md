---

nav_title: Scenario — Docs Health
public_publish: true
audience: public
product_area: lenses
learning_level: overview
section: builders
description: Reading Docs Health signals and work items before agent remediation.
status: shipped
tier: builder
handbook_area: builders
page_type: topic
---

# Scenario — Docs Health remediation

## Scenario summary

Reconcile **`/api/docs-health/*`** summaries and work items (**GET-first**) before handing fixes to Cursor agents.

## User role

Docs Health operator or reviewer.

## Starting state

- Local Lenses with Docs Health overlays enabled ([Docs Health in Studio](15-docs-health.md)).

## Steps

1. Read summary counts to learn whether issues are centralized or repo-specific.
2. Pull work items sorted by severity; confirm repo slug paths match filesystem expectations.
3. Pair each item with a human-readable Markdown path surfaced in payloads.

## Example input / output

Do **not** paste production tokens; treat payloads as described in handbook tables plus [`sample-docs-health-work-item.json`](../examples/sample-docs-health-work-item.json) shape.

### Expected intermediate state

Every accepted issue has an owner recorded before branching.

## Verification

Feeds return HTTP 200 on localhost and align with Studio cards from [First Docs Health scan](05-studio-101_02-first-docs-health-scan.md).

## Failure / recovery

If payloads disagree with cloned repos, re-run host scans ([Workspace setup — scan host](03-workspace-setup_03-scan-host.md)) and escalate before submodule edits.

## Related API/schema docs

[Schemas and API for builders](16-schemas-and-api-for-builders.md) + [`sample-docs-health-work-item.json`](../examples/sample-docs-health-work-item.json).

## Canonical path

Still read [Docs Health in Studio](15-docs-health.md) for UI-specific guidance alongside this API-first drill.
