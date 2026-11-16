import path from "path";
import { test, expect } from "@playwright/test";
import { _electron as electron } from "@playwright/test";

const appDir = path.join(__dirname, "..");
const repoRoot = path.join(appDir, "..");

test.describe("forge-lenses desktop", () => {
  test("electron shell opens a browser window", async () => {
    const electronApp = await electron.launch({
      cwd: appDir,
      args: [".", "--no-sandbox"],
      env: {
        ...process.env,
        LENSES_WORKSPACE_ROOT: process.env.LENSES_WORKSPACE_ROOT ?? repoRoot,
        PYTHONPATH: process.env.PYTHONPATH ?? repoRoot,
      },
    });
    try {
      const window = await electronApp.firstWindow({ timeout: 180_000 });
      await window.waitForLoadState("domcontentloaded");
      await expect(window).toBeTruthy();
    } finally {
      await electronApp.close();
    }
  });
});
