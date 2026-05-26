# PDCA 01 — Registry health

## Plan

Read `lenses/sticker_board.py` (`repair_registry`, `registry_snapshot`) and `BoardsArtifactsHub.tsx` error states.

## Do

Ensure `POST /api/sticker-board-registry` with `action: repair_registry` works. Hub shows **Fix registry** when `validation_issues` present. Document env: Lenses on `LENSES_BASE_URL`.

## Check

`./scripts/studio-boards-workshop-pdca/checks/smoke-boards-studio.sh`

## Adjust

Fix any failing registry fetch or validation repair edge cases.
