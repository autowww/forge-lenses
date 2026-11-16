/**
 * Electron Forge Studio — forge-accessibility-leo product map board + Stickerboard APIs.
 *
 * Uses the real Code workspace (child repo forge-accessibility-leo) and an existing
 * registry board when present; otherwise creates a workshop kickoff board via API.
 *
 *   npx playwright test e2e/studio-boards-forge-accessibility-leo.spec.ts
 */
import fs from "fs";
import path from "path";
import { test, expect } from "@playwright/test";
import { _electron as electron } from "@playwright/test";
import { waitForStudioMainWindow } from "./helpers/electron-studio-window";
import { reserveLoopbackPort } from "./helpers/reserve-port";

const appDir = path.join(__dirname, "..");
const repoRoot = path.join(appDir, "..");
const workspaceRoot = process.env.LENSES_E2E_WORKSPACE || path.join(repoRoot, "..");
const a11yRepo = path.join(workspaceRoot, "forge-accessibility-leo");
const projectSlug = "forge-accessibility-leo";

const PREFERRED_BOARD_ID = process.env.LENSES_E2E_A11Y_BOARD_ID || "XwsPN3GfCW2I30CH19Vs8M";

function registryBoardId(): string | null {
  const regPath = path.join(workspaceRoot, ".lenses-local", "sticker-board-registry.json");
  if (!fs.existsSync(regPath)) return null;
  const reg = JSON.parse(fs.readFileSync(regPath, "utf8")) as {
    projects?: Record<string, { id: string; label?: string }[]>;
  };
  const entries = reg.projects?.[projectSlug];
  if (!Array.isArray(entries) || entries.length === 0) return null;
  const hit = entries.find((e) => e.id === PREFERRED_BOARD_ID);
  return hit?.id ?? entries[0]?.id ?? null;
}

function boardDataFile(boardId: string): string {
  return path.join(workspaceRoot, ".lenses-local", "sticker-boards", `${boardId}.json`);
}

test.describe("Forge Studio — forge-accessibility-leo boards", () => {
  test.beforeAll(() => {
    test.skip(!fs.existsSync(a11yRepo), `missing repo: ${a11yRepo}`);
    test.skip(!fs.existsSync(workspaceRoot), `missing workspace: ${workspaceRoot}`);
  });

  test("loads accessibility-leo board and Stickerboard share APIs", async () => {
    const lensesPort = await reserveLoopbackPort();
    let boardId = registryBoardId();
    const boardFile = boardId ? boardDataFile(boardId) : "";
    if (!boardId || !fs.existsSync(boardFile)) {
      boardId = null;
    }

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

      if (!boardId) {
        const fixture = path.join(
          repoRoot,
          "tests",
          "fixtures",
          "workshop_kickoff_a11y.md",
        );
        const md = fs.readFileSync(fixture, "utf8");
        const created = await window.evaluate(
          async ({ project, mdText }) => {
            const res = await fetch("/api/sticker-board-registry", {
              method: "POST",
              headers: { "Content-Type": "application/json", Accept: "application/json" },
              credentials: "include",
              body: JSON.stringify({
                action: "create",
                payload: {
                  project,
                  label: "A11y Studio kickoff (E2E)",
                  session_template: "workshop_kickoff",
                  workshop_md_text: mdText,
                  prefill: true,
                },
              }),
            });
            const body = (await res.json()) as { ok?: boolean; board_id?: string; error?: string };
            return { httpOk: res.ok, ...body };
          },
          { project: projectSlug, mdText: md },
        );
        expect(created.httpOk).toBe(true);
        expect(created.board_id).toBeTruthy();
        boardId = String(created.board_id);
      }

      const boardUrl = `${origin}/studio/board/${encodeURIComponent(boardId!)}?phase=discover`;
      await window.goto(boardUrl, { waitUntil: "domcontentloaded", timeout: 120_000 });

      await expect(window.getByRole("heading", { name: "Could not load board" })).toHaveCount(0, {
        timeout: 60_000,
      });
      await expect(window.getByRole("button", { name: "Save changes" })).toBeVisible({
        timeout: 60_000,
      });
      await expect(window.locator(".fs-sticker-kanban").first()).toBeVisible({
        timeout: 60_000,
      });

      const shareCfg = await window.evaluate(async () => {
        const res = await fetch("/api/sticker-board-share/config", { credentials: "include" });
        return res.json() as Promise<{ public_base?: string; public_base_configured?: boolean }>;
      });
      expect(shareCfg.public_base_configured).toBe(true);

      const share = await window.evaluate(async (bid) => {
        const res = await fetch("/api/sticker-board-share", {
          method: "POST",
          headers: { "Content-Type": "application/json", Accept: "application/json" },
          credentials: "include",
          body: JSON.stringify({
            action: "start",
            board_id: bid,
            guest_role: "view",
          }),
        });
        const body = (await res.json()) as {
          ok?: boolean;
          share_token?: string;
          public_url?: string;
          board_label?: string;
        };
        return { httpOk: res.ok, ...body };
      }, boardId);
      expect(share.httpOk).toBe(true);
      expect(share.share_token).toBeTruthy();
      expect(String(share.public_url || "")).toContain("#/");

      const prefixedMeta = await window.evaluate(async (token) => {
        const res = await fetch(
          `/stickerboard/api/sticker-board-share?token=${encodeURIComponent(token)}`,
          { credentials: "include" },
        );
        const body = (await res.json()) as { ok?: boolean; board_id?: string; board_label?: string };
        return { httpOk: res.ok, ...body };
      }, share.share_token);
      expect(prefixedMeta.httpOk).toBe(true);
      expect(prefixedMeta.board_id).toBe(boardId);
      expect(prefixedMeta.board_label).toBeTruthy();

      const scopedBoard = await window.evaluate(
        async ({ token, bid }) => {
          await fetch("/api/sticker-board-share/join", {
            method: "POST",
            headers: { "Content-Type": "application/json", Accept: "application/json" },
            credentials: "include",
            body: JSON.stringify({ share_token: token }),
          });
          const res = await fetch(
            `/stickerboard/api/sticker-board?board_id=${encodeURIComponent(bid)}`,
            { credentials: "include" },
          );
          const body = (await res.json()) as { board_id?: string; board_not_found?: boolean };
          return { httpOk: res.ok, board_id: body.board_id };
        },
        { token: share.share_token, bid: boardId },
      );
      expect(scopedBoard.httpOk).toBe(true);
      expect(scopedBoard.board_id).toBe(boardId);
    } finally {
      await electronApp.close();
    }
  });
});
