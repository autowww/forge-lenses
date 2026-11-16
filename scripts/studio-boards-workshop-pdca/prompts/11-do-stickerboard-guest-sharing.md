# PDCA 11 — Stickerboard guest sharing

## Plan

Implement Forge Lenses Stickerboard per `docs/handbook-public/16-stickerboard-sharing.md`:

- `lenses/sticker_board_share.py` — random tokens, start/revoke/join
- `serve.py` — share-scope 401, port 9999 listener, APIs
- Qualitative `impact_label` / `effort_label` on stickers (board v4)
- `lenses-enterprise` — `StickerboardGuestApp`, `build:stickerboard`, facilitator share panel

## Do

1. Run `pytest tests/test_sticker_board_share.py tests/test_sticker_board_session.py -q`
2. `cd lenses-enterprise && npm run build:stickerboard`
3. Smoke: Lenses on 8080; `curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:9999/` → 200
4. Smoke: `curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:9999/studio/` → 401

## Check

- Facilitator can start sharing from Studio board editor
- Copied URL uses `VITE_STICKERBOARD_PUBLIC_BASE`
- Guest Edit can POST board; View cannot

## Adjust

Fix failing tests only; no scope creep.
