import type { ElectronApplication, Page } from "@playwright/test";

const STUDIO_URL = /:\/\/127\.0\.0\.1:\d+\/studio\/?/;

/**
 * Electron opens a splash window first; the main Studio window loads /studio/ later.
 */
export async function waitForStudioMainWindow(
  app: ElectronApplication,
  timeoutMs = 180_000,
): Promise<Page> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    for (const page of app.windows()) {
      if (STUDIO_URL.test(page.url())) {
        await page.waitForLoadState("domcontentloaded").catch(() => {});
        return page;
      }
    }
    const remaining = deadline - Date.now();
    if (remaining <= 0) break;
    try {
      const page = await app.waitForEvent("window", {
        timeout: Math.min(2_000, remaining),
      });
      if (STUDIO_URL.test(page.url())) {
        await page.waitForLoadState("domcontentloaded").catch(() => {});
        return page;
      }
    } catch {
      /* poll again */
    }
    await new Promise((r) => setTimeout(r, 250));
  }
  const urls = app.windows().map((w) => w.url()).join(", ") || "(none)";
  throw new Error(`Studio main window not found within ${timeoutMs}ms. Open windows: ${urls}`);
}
