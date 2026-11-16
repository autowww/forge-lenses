# Studio boards workshop — master plan

## Acceptance

- Studio `/studio/board` hub creates boards from session templates.
- `/studio/board/:id` editor supports kanban DnD, impact/effort, workshop phases.
- `product_map_workshop` prefills from project WBS via `GET /api/forge-work-model` data path.
- `pytest tests/test_sticker_board_session.py tests/test_board_product_map.py` passes.
- `cd lenses-enterprise && npm run build` succeeds.

## Key paths

- `lenses/sticker_board.py`, `lenses/board_product_map.py`, `lenses/serve.py`
- `lenses-enterprise/src/components/boards/`
- `kitchensink/css/fs-sticker-board.css`

## PDCA

Work prompts `01`–`10` in order unless `--only` is set on `run-boards-workshop-pdca.sh`.
