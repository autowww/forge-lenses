---

nav_title: Scenario — Docs inventory refresh
public_publish: true
audience: public
product_area: lenses
learning_level: reference
section: builders
description: Regenerating inventory JSON after nav or handbook coverage changes.
status: shipped
tier: builder
handbook_area: builders
page_type: topic
---

# Scenario — Docs inventory refresh cadence

## Scenario summary

Regenerate [`documentation-inventory.json`](../strategy/documentation-inventory.json) after meaningful `docs/nav.yml`, schema, or API route edits so freshness gates stay green.

## User role

Handbook maintainer.

## Starting state

- Clean tree aside from deliberate doc edits.

## Steps

1. `python3 generator/export-docs-inventory.py`
2. `python3 scripts/check-docs-inventory-fresh.py`
3. Commit JSON when materially changed along with explanatory Markdown.

## Example input

```bash
python3 generator/export-docs-inventory.py
python3 scripts/check-docs-inventory-fresh.py --write   # optional auto-rewrite
```

## Example output or expected state

`check-docs-inventory-fresh.py` exits 0; diff shows fingerprint fields only.

## Verification

Included automatically in `bash scripts/check-docs.sh`.

## Failure / recovery

Re-run exporters from repo root (`PYTHONPATH=`), inspect merge conflicts in inventory JSON.

## Related API/schema docs

Strategy diagrams note: **[diagram-and-scenario-gap-bridge-notes.md on GitHub](https://github.com/autowww/forge-lenses/blob/main/docs/strategy/diagram-and-scenario-gap-bridge-notes.md)**.
