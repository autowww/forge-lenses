# PDCA 02 — Session templates API

## Plan

Confirm `BOARD_SESSION_TEMPLATES`, `initial_state_for_session`, board version 3, `validate_board` for impact/effort.

## Do

Implement or complete missing pieces in `sticker_board.py`. Add/extend `tests/test_sticker_board_session.py`.

## Check

`python3 -m pytest tests/test_sticker_board_session.py -q`

## Adjust

Fix validation errors; keep BOARD_VERSION 3 compatible with v2 reads.
