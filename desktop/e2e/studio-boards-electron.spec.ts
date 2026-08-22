/**
 * Electron Forge Studio — sticker board editor loads after launch.
 *
 * Isolated temp workspace (seeded registry + board JSON), dedicated LENSES_PORT
 * so Electron never attaches to another :8080 instance.
 *
 *   npx playwright test e2e/studio-boards-electron.spec.ts
 */
import fs from "fs";
import os from "os";
import path from "path";
import { test, expect } from "@playwright/test";
import { _electron as electron } from "@playwright/test";
import { waitForStudioMainWindow } from "./helpers/electron-studio-window";
import { reserveLoopbackPort } from "./helpers/reserve-port";
import { E2E_BOARD_ID, seedStickerBoardWorkspace } from "./helpers/sticker-board-seed";

const appDir = path.join(__dirname, "..");
const repoRoot = path.join(appDir, "..");

test.describe("Forge Studio Electron — sticker boards", () => {
  test("opens seeded board in workshop editor", async () => {
    const workspaceRoot = fs.mkdtempSync(path.join(os.tmpdir(), "lenses-e2e-ws-"));
    seedStickerBoardWorkspace(workspaceRoot, E2E_BOARD_ID);
    const lensesPort = await reserveLoopbackPort();

    const electronApp = await electron.launch({
      cwd: appDir,
      args: [".", "--no-sandbox"],
      env: {
        ...process.env,
        LENSES_WORKSPACE_ROOT: workspaceRoot,
        LENSES_PORT: String(lensesPort),
        LENSES_STICKERBOARD_PORT: "0",
        LENSES_STUDIO_UI: "1",
        LENSES_EXPERIMENTAL_BLUEPRINTS_WIZARD: "1",
        LENSES_SEARCH_REINDEX_ON_START: "0",
        PYTHONPATH: process.env.PYTHONPATH ?? repoRoot,
      },
    });

    try {
      const window = await waitForStudioMainWindow(electronApp);
      const origin = new URL(window.url()).origin;
      expect(origin).toBe(`http://127.0.0.1:${lensesPort}`);

      const boardUrl = `${origin}/studio/board/${encodeURIComponent(E2E_BOARD_ID)}?phase=discover`;
      await window.goto(boardUrl, { waitUntil: "domcontentloaded", timeout: 120_000 });

      await expect(window.getByRole("heading", { name: "Could not load board" })).toHaveCount(0, {
        timeout: 60_000,
      });

      await expect(window.getByRole("button", { name: "Save changes" })).toBeVisible({
        timeout: 60_000,
      });

      await expect(window.locator(".fs-sticker-card__title").filter({ hasText: "E2E card" })).toBeVisible({
        timeout: 30_000,
      });

      await expect(window.locator(".fs-sticker-kanban").first()).toBeVisible({
        timeout: 30_000,
      });

      const share = await window.evaluate(async (boardId) => {
        const res = await fetch("/api/sticker-board-share", {
          method: "POST",
          headers: { "Content-Type": "application/json", Accept: "application/json" },
          credentials: "include",
          body: JSON.stringify({
            action: "start",
            board_id: boardId,
            guest_role: "view",
          }),
        });
        const body = (await res.json()) as { ok?: boolean; share_token?: string; error?: string };
        return { httpOk: res.ok, ...body };
      }, E2E_BOARD_ID);
      expect(share.httpOk).toBe(true);
      expect(share.ok).not.toBe(false);
      expect(share.share_token).toBeTruthy();
    } finally {
      await electronApp.close();
    }
  });
});
