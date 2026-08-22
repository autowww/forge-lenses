import fs from "fs";
import path from "path";

/** Stable id for registry round-trip (16–40 alnum/underscore). */
export const E2E_BOARD_ID = "e2eBrd000000000001";

export function seedStickerBoardWorkspace(workspaceRoot: string, boardId: string): void {
  const local = path.join(workspaceRoot, ".lenses-local");
  const boardsDir = path.join(local, "sticker-boards");
  fs.mkdirSync(boardsDir, { recursive: true });
  const registry = {
    version: 1,
    projects: {
      _unassigned: [
        {
          id: boardId,
          label: "E2E sticker board",
          storage: "local",
        },
      ],
    },
  };
  fs.writeFileSync(
    path.join(local, "sticker-board-registry.json"),
    JSON.stringify(registry, null, 2),
    "utf8",
  );
  const board = {
    version: 4,
    board_storage: "local",
    template: "kanban",
    session_template: "roadmap_session",
    workshop_phase: "discover",
    columns: [
      { id: "now", title: "Now" },
      { id: "next", title: "Next" },
    ],
    saved_kanban_columns: [],
    stickers: [
      {
        id: "card1",
        title: "E2E card",
        body: "Playwright seed",
        column_id: "now",
        order: 0,
        x: 0,
        y: 0,
      },
    ],
  };
  fs.writeFileSync(
    path.join(boardsDir, `${boardId}.json`),
    JSON.stringify(board, null, 2),
    "utf8",
  );
}
