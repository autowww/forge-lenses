# JSON examples

Rules:

1. For every **`docs/schemas/*.schema.json`**, authors must ship a matching **`sample-<stem>.json`** file (same `<stem>` as the schema basename).
2. CI (`tests/test_docs_schemas.py`) validates **every** pair using Draft 2020-12 plus the `referencing` registry.

Reader-facing summaries live in **`docs/handbook-public/19-examples-hub.md`**.
