# PDCA 10 — Product map prefill

## Plan

Read `lenses/board_product_map.py`, `forge_work_model.py`, `wbs_management.py`. Env: `BOARDS_PREFILL_REPO` (workspace child slug).

## Do

- `hydrate_board_from_product_map` maps epics → capabilities, stories → journey.
- `registry_apply` create with `session_template: product_map_workshop`, `prefill: true`, `_workspace_scan_state` from serve.
- Hub: **Product map workshop** + project dropdown + **Create from project**.

## Check

```bash
export BOARDS_PREFILL_REPO=forge-lenses  # or a child with WBS.md
python3 -m pytest tests/test_board_product_map.py -q
```

## Adjust

If no WBS: board columns only + Studio `StatePanel` with `prefill_message` (no silent failure).
