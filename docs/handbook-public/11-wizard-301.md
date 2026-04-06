---
nav_title: Wizard 301
public_publish: true
audience: public
product_area: wizard
tier: "301"
---

# Wizard 301 — Advanced usage

## What it is

Deeper use of the Wizard: **artifact bundles**, **Refine** and LLM-assisted steps, **review and recheck**, and **Cursor Launch Pack** packaging.

## When to use it

After [Wizard 201](10-wizard-201.md), when you are tuning outputs or exports.

## Prerequisites

- Stable **server-enabled** sessions when possible ([Wizard 201](10-wizard-201.md)).

## Steps

### Artifact bundles

Depending on **Target & output pack**, generation can emphasize **planning**, **engineering**, **execution**, or **full stack** slices. Labels vary by version — treat them as emphasis, not automatic repo edits.

### Refine

Steps like **Understanding** may offer **Refine**. You stay in control: read output, edit notes, refine again. Paste **constraints** and **non-goals** explicitly.

### Review, approve, recheck

Use **Review & generate** as a gate: fix upstream notes and regenerate rather than patching only the preview. **Recheck / repair** runs consistency checks; **refresh** after you persist new summaries.

### Cursor Launch Pack

The last step can package context for **Cursor** (or another editor). Read warnings; strict modes may block export until slices are locked.

### Optional integrations

Some environments offer extra steps (for example creating a remote repository after confirmation). Whether those appear depends on **server policy and configuration** where you run Lenses — not on fields in your session file. If your organization restricts that flow, complete exports manually and place artifacts in your own repo.

Operator setup for experimental Wizard options and repository integrations is documented for maintainers in the **forge-lenses** repository on GitHub.

## How to verify success

- Exports match your policy; recheck passes or you knowingly accept gaps.

## What to do next

- [Troubleshooting](12-troubleshooting.md)
