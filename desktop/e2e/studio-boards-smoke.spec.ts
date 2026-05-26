/**
 * Sticker board API + Studio editor smoke (HTTP).
 *
 * Prereq: `python3 -m lenses` on LENSES_E2E_BASE (default :8080), workspace with write access.
 *
 *   LENSES_E2E=1 npx playwright test e2e/studio-boards-smoke.spec.ts
 */
import { test, expect } from "@playwright/test";

const base = (process.env.LENSES_E2E_BASE || "http://127.0.0.1:8080").replace(/\/$/, "");
const run = process.env.LENSES_E2E === "1";
const d = run ? test.describe : test.describe.skip;

d("Sticker board HTTP (Studio backend)", () => {
  test("GET /api/sticker-board-registry returns JSON", async ({ request }) => {
    const res = await request.get(`${base}/api/sticker-board-registry`);
    expect(res.ok()).toBeTruthy();
    const j = (await res.json()) as Record<string, unknown>;
    expect(j.version).toBe(1);
    expect(j.projects).toBeTruthy();
  });

  test("create board via registry then load in Studio API", async ({ request }) => {
    const label = `pw-create-${Date.now()}`;
    const createRes = await request.post(`${base}/api/sticker-board-registry`, {
      data: {
        action: "create",
        payload: {
          project: "_unassigned",
          label,
          storage: "local",
          session_template: "roadmap_session",
        },
      },
    });
    expect(createRes.ok()).toBeTruthy();
    const created = (await createRes.json()) as { ok?: boolean; board_id?: string; error?: string };
    expect(created.ok).not.toBe(false);
    expect(created.board_id).toBeTruthy();
    const bid = String(created.board_id);

    const loadRes = await request.get(
      `${base}/api/sticker-board?board_id=${encodeURIComponent(bid)}`,
    );
    expect(loadRes.ok()).toBeTruthy();
    const board = (await loadRes.json()) as Record<string, unknown>;
    expect(board.error).toBeUndefined();
    expect(board.template).toBe("kanban");
    expect(Array.isArray(board.columns)).toBe(true);
    expect((board.columns as unknown[]).length).toBeGreaterThan(0);
  });
});
