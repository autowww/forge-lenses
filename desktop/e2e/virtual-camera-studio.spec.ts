/**
 * Virtual Camera Studio — Electron + HTTP smoke on dedicated port.
 *
 *   cd forge-lenses/desktop && npx playwright test e2e/virtual-camera-studio.spec.ts
 */
import path from "path";
import { test, expect } from "@playwright/test";
import { _electron as electron } from "@playwright/test";
import { waitForStudioMainWindow } from "./helpers/electron-studio-window";
import { reserveLoopbackPort } from "./helpers/reserve-port";

const appDir = path.join(__dirname, "..");
const repoRoot = path.join(appDir, "..");
const workspaceRoot = path.join(repoRoot, "..");

function preferredInputFormat(
  formats?: Array<{ fourcc?: string }>,
): string {
  const fourccs = (formats ?? []).map((f) => (f.fourcc || "").toUpperCase());
  if (fourccs.some((f) => f === "MJPG" || f === "MJPEG")) return "MJPEG";
  if (fourccs.includes("GREY")) return "GREY";
  return "MJPEG";
}

type PhysicalCamera = {
  device_path?: string;
  stable_id?: string;
  label?: string;
  formats?: Array<{ fourcc?: string }>;
};

function pickSourceCamera(physical: PhysicalCamera[]): PhysicalCamera | undefined {
  const mjpg = physical.find((c) =>
    c.formats?.some((f) => (f.fourcc || "").toUpperCase() === "MJPG"),
  );
  return mjpg ?? physical[0];
}

test.describe("Virtual Camera Studio", () => {
  test("HTTP API enabled on dedicated instance", async ({ request }) => {
    const lensesPort = await reserveLoopbackPort();
    const base = `http://127.0.0.1:${lensesPort}`;

    const { spawn } = await import("child_process");
    const child = spawn(
      "python3",
      ["-m", "lenses", "--host", "127.0.0.1", "--port", String(lensesPort)],
      {
        cwd: repoRoot,
        env: {
          ...process.env,
          PYTHONPATH: repoRoot,
          LENSES_WORKSPACE_ROOT: workspaceRoot,
          LENSES_EXPERIMENTAL_VIRTUAL_CAMERA: "1",
          LENSES_STICKERBOARD_PORT: "0",
          LENSES_SEARCH_REINDEX_ON_START: "0",
        },
        stdio: "ignore",
      },
    );

    try {
      const deadline = Date.now() + 90_000;
      let enabled = false;
      while (Date.now() < deadline) {
        try {
          const res = await request.get(`${base}/api/virtual-camera/enabled`);
          if (res.ok()) {
            const j = (await res.json()) as { enabled?: boolean; ok?: boolean };
            if (j.ok && j.enabled) {
              enabled = true;
              break;
            }
          }
        } catch {
          /* server still starting */
        }
        await new Promise((r) => setTimeout(r, 500));
      }
      expect(enabled).toBe(true);

      const vdiRes = await request.get(`${base}/api/virtual-camera/vdi-readiness`);
      expect(vdiRes.ok()).toBeTruthy();
      const vdi = (await vdiRes.json()) as { recommended_preset_id?: string; ok?: boolean };
      expect(vdi.ok).toBe(true);
      expect(vdi.recommended_preset_id).toBe("avd_teams");

      const pageRes = await request.get(`${base}/studio/labs/virtual-camera`);
      expect(pageRes.ok()).toBeTruthy();
      const html = await pageRes.text();
      expect(html).not.toContain("This lab is disabled");

      const camerasRes = await request.get(`${base}/api/virtual-camera/cameras`);
      expect(camerasRes.ok()).toBeTruthy();
      const cameras = (await camerasRes.json()) as {
        physical?: PhysicalCamera[];
        virtual?: Array<{ device_path?: string }>;
      };
      const sourceCam = pickSourceCamera(cameras.physical ?? []);
      const device = sourceCam?.device_path;
      if (device) {
        const inputFormat = preferredInputFormat(sourceCam?.formats);
        const previewUrl = `${base}/api/virtual-camera/preview/_source?device=${encodeURIComponent(device)}&width=640&height=360&fps=15&input_format=${encodeURIComponent(inputFormat)}`;
        const controller = new AbortController();
        const abortTimer = setTimeout(() => controller.abort(), 3000);
        let buf = Buffer.alloc(0);
        try {
          const res = await fetch(previewUrl, { signal: controller.signal });
          expect(res.ok).toBe(true);
          const ct = res.headers.get("content-type") || "";
          expect(ct).toContain("multipart/x-mixed-replace");
          expect(ct).toContain("boundary=frame");
          const reader = res.body?.getReader();
          if (reader) {
            const chunks: Uint8Array[] = [];
            let total = 0;
            while (total < 65536) {
              const { done, value } = await reader.read();
              if (done || !value) break;
              chunks.push(value);
              total += value.length;
            }
            buf = Buffer.concat(chunks);
          }
        } catch (err) {
          if (!(err instanceof Error) || err.name !== "AbortError") {
            throw err;
          }
        } finally {
          clearTimeout(abortTimer);
        }
        expect(buf.length).toBeGreaterThan(1000);
        const jpegIdx = buf.indexOf(Buffer.from([0xff, 0xd8]));
        expect(jpegIdx).toBeGreaterThan(-1);

        await request.post(`${base}/api/virtual-camera/preview/stop`, { data: { device } });
        await new Promise((r) => setTimeout(r, 500));
      }

      const virtualDev = cameras.virtual?.[0]?.device_path;
      if (device && virtualDev && sourceCam) {
        const inputFormat = preferredInputFormat(sourceCam.formats);
        const createRes = await request.post(`${base}/api/virtual-camera/profiles`, {
          data: {
            profile: {
              name: "E2E start probe",
              source: {
                stable_id: sourceCam.stable_id ?? "",
                device_path: device,
                label: sourceCam.label ?? "",
              },
              virtual: {
                device_path: virtualDev,
                card_label: "E2E Virtual",
              },
              resolution: { width: 640, height: 360 },
              fps: 15,
              input_format: inputFormat,
              output_format: "YUYV",
              blur_level: "off",
            },
          },
        });
        expect(createRes.ok()).toBeTruthy();
        const created = (await createRes.json()) as { profile?: { id?: string } };
        const profileId = created.profile?.id;
        expect(profileId).toBeTruthy();

        const startRes = await request.post(
          `${base}/api/virtual-camera/profiles/${encodeURIComponent(profileId!)}/start`,
          { data: {} },
        );
        expect(startRes.ok()).toBeTruthy();
        const started = (await startRes.json()) as { ok?: boolean; state?: string };
        expect(started.ok).toBe(true);
        expect(started.state).toBe("running");

        const processedPreview = await fetch(
          `${base}/api/virtual-camera/preview/${encodeURIComponent(profileId!)}?view=processed`,
        );
        expect(processedPreview.ok).toBe(true);
        const pct = processedPreview.headers.get("content-type") || "";
        expect(pct).toContain("multipart/x-mixed-replace");
        const pController = new AbortController();
        const pAbortTimer = setTimeout(() => pController.abort(), 4000);
        let previewBuf = Buffer.alloc(0);
        try {
          const pReader = processedPreview.body?.getReader();
          if (pReader) {
            const deadline = Date.now() + 3500;
            while (Date.now() < deadline && previewBuf.length < 65536) {
              const { done, value } = await pReader.read();
              if (done || !value) break;
              previewBuf = Buffer.concat([previewBuf, Buffer.from(value)]);
            }
            pReader.cancel().catch(() => {});
          }
        } catch (err) {
          if (!(err instanceof Error) || err.name !== "AbortError") {
            throw err;
          }
        } finally {
          clearTimeout(pAbortTimer);
        }
        expect(previewBuf.length).toBeGreaterThan(1000);
        expect(previewBuf.indexOf(Buffer.from([0xff, 0xd8]))).toBeGreaterThan(-1);

        await request.post(
          `${base}/api/virtual-camera/profiles/${encodeURIComponent(profileId!)}/stop`,
          { data: {} },
        );
        await request.post(
          `${base}/api/virtual-camera/profiles/${encodeURIComponent(profileId!)}/delete`,
          { data: {} },
        );
      }
    } finally {
      child.kill("SIGTERM");
    }
  });

  test("Electron shell opens VC page with new profile form", async () => {
    const lensesPort = await reserveLoopbackPort();

    const electronApp = await electron.launch({
      cwd: appDir,
      args: [".", "--no-sandbox"],
      env: {
        ...process.env,
        LENSES_WORKSPACE_ROOT: workspaceRoot,
        LENSES_PORT: String(lensesPort),
        LENSES_STUDIO_UI: "1",
        LENSES_VIRTUAL_CAMERA_STUDIO: "1",
        LENSES_EXPERIMENTAL_VIRTUAL_CAMERA: "1",
        LENSES_STICKERBOARD_PORT: "0",
        LENSES_SEARCH_REINDEX_ON_START: "0",
        LENSES_EXPERIMENTAL_BLUEPRINTS_WIZARD: "0",
        LENSES_EXPERIMENTAL_ORCHESTRATION_GRAPH: "0",
        LENSES_EXPERIMENTAL_AGENTIC_BRIDGE_B3: "0",
        LENSES_EXPERIMENTAL_FOUNDRY: "0",
        PYTHONPATH: process.env.PYTHONPATH ?? repoRoot,
      },
    });

    try {
      const window = await waitForStudioMainWindow(electronApp);
      const origin = new URL(window.url()).origin;
      expect(origin).toBe(`http://127.0.0.1:${lensesPort}`);

      const vcUrl = `${origin}/studio/labs/virtual-camera`;
      await window.goto(vcUrl, { waitUntil: "domcontentloaded", timeout: 120_000 });

      await expect(window.getByText("This lab is disabled")).toHaveCount(0, { timeout: 60_000 });
      await expect(window.getByRole("heading", { name: "Virtual Camera Studio" }).first()).toBeVisible({
        timeout: 60_000,
      });

      await expect(window.getByRole("heading", { name: "Azure Cloud VDI / Teams" })).toBeVisible({
        timeout: 30_000,
      });
      await expect(window.getByRole("button", { name: "Apply AVD Teams preset" })).toBeVisible();

      await expect(window.getByRole("button", { name: "New profile" })).toBeVisible({ timeout: 30_000 });
      await window.getByRole("button", { name: "New profile" }).click();

      await expect(window.getByRole("heading", { name: "New profile" })).toBeVisible({ timeout: 15_000 });
      await expect(window.getByText("Source preview")).toBeVisible({ timeout: 15_000 });

      const sourceSelect = window.locator("label").filter({ hasText: "Source camera" }).locator("select");
      await expect(sourceSelect).toBeVisible();
      const optionCount = await sourceSelect.locator("option").count();
      expect(optionCount).toBeGreaterThan(1);

      const brand = window.locator(".le-brand-text");
      await expect(brand).toContainText("Virtual Camera Studio");
      await expect(brand).not.toContainText("Forge Studio");

      const previewImg = window.getByAltText("Source camera preview");
      await expect(previewImg).toBeVisible({ timeout: 15_000 });
      await expect(async () => {
        const nw = await previewImg.evaluate((el: HTMLImageElement) => el.naturalWidth);
        expect(nw).toBeGreaterThan(0);
      }).toPass({ timeout: 20_000 });
    } finally {
      await electronApp.close();
    }
  });
});
