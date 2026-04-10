#!/usr/bin/env node
/**
 * Lenses Studio screenshot tour — Playwright Chromium, YAML-defined steps.
 * Run from desktop/: node studio-explore/runner.mjs [--tour PATH] [--out DIR] [--headed] [--repo-root PATH]
 */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { chromium } from "playwright-core";
import yaml from "js-yaml";
import { spawnSync } from "child_process";

function parseArgs(argv) {
  const out = { tour: null, outDir: null, headed: false, repoRoot: null };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--tour") out.tour = argv[++i];
    else if (a === "--out") out.outDir = argv[++i];
    else if (a === "--headed") out.headed = true;
    else if (a === "--repo-root") out.repoRoot = argv[++i];
    else if (a === "-h" || a === "--help") {
      console.log(`Usage: node studio-explore/runner.mjs [--tour tour.yaml] [--out dir] [--headed] [--repo-root path]
  Env: LENSES_BASE_URL (default http://127.0.0.1:8080), FORGE_LENSES_ROOT`);
      process.exit(0);
    }
  }
  return out;
}

function defaultRepoRoot() {
  if (process.env.FORGE_LENSES_ROOT) return path.resolve(process.env.FORGE_LENSES_ROOT);
  const here = path.dirname(fileURLToPath(import.meta.url));
  return path.resolve(here, "..", "..");
}

function gitHead(cwd) {
  const r = spawnSync("git", ["rev-parse", "--short", "HEAD"], { cwd, encoding: "utf8" });
  return r.status === 0 ? r.stdout.trim() : "unknown";
}

function sanitizeFolderId(id) {
  return String(id).replace(/[^a-zA-Z0-9._-]+/g, "_").replace(/^\.+/, "") || "folder";
}

/** Multi-level output path from YAML `directory` (e.g. flow/Workspace). */
function sanitizePathSegment(seg) {
  const s = String(seg).trim();
  if (!s) return "";
  return s.replace(/[^a-zA-Z0-9._ -]+/g, "_").replace(/^\.+/, "").replace(/\s+/g, "-") || "segment";
}

function resolveFolderDir(outRoot, folder) {
  if (folder.directory && typeof folder.directory === "string") {
    const parts = folder.directory
      .split("/")
      .map((p) => sanitizePathSegment(p))
      .filter(Boolean);
    if (parts.length) return path.join(outRoot, ...parts);
  }
  return path.join(outRoot, sanitizeFolderId(folder.id || "folder"));
}

/** Align Studio shell with Flow vs Artifacts top nav (cookie workspace_lens). */
async function applyWorkspaceLens(context, page, baseUrl, lens) {
  if (lens !== "flow" && lens !== "artifacts") return;
  await context.addCookies([
    { name: "workspace_lens", value: lens, url: baseUrl },
    { name: "nav_mode", value: lens, url: baseUrl },
  ]);
  await page.goto(buildUrl(baseUrl, "/studio/"), { waitUntil: "domcontentloaded", timeout: 60_000 });
  await new Promise((r) => setTimeout(r, 900));
}

function ensureDir(p) {
  fs.mkdirSync(p, { recursive: true });
}

function buildUrl(baseUrl, pth) {
  if (/^https?:\/\//i.test(pth)) return pth;
  const base = baseUrl.replace(/\/$/, "");
  const rel = pth.startsWith("/") ? pth : `/${pth}`;
  return `${base}${rel}`;
}

async function runStep(page, step, baseUrl, viewport) {
  const url = buildUrl(baseUrl, step.path);
  await page.setViewportSize(viewport);
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60_000 });
  if (step.wait_selector) {
    await page.waitForSelector(step.wait_selector, { state: "visible", timeout: 45_000 });
  }
  const w = Number(step.wait_ms) || 0;
  if (w > 0) await new Promise((r) => setTimeout(r, w));
  if (step.click_selector) {
    await page.click(step.click_selector, { timeout: 15_000 });
    const after = Number(step.wait_after_click_ms) || 500;
    if (after > 0) await new Promise((r) => setTimeout(r, after));
  }
  return page.url();
}

async function main() {
  const args = parseArgs(process.argv);
  const repoRoot = args.repoRoot ? path.resolve(args.repoRoot) : defaultRepoRoot();
  const desktopDir = path.join(repoRoot, "desktop");
  const tourPath = args.tour
    ? path.resolve(args.tour)
    : path.join(desktopDir, "studio-explore", "tours", "explore-default", "tour.yaml");

  if (!fs.existsSync(tourPath)) {
    console.error(`Tour not found: ${tourPath}`);
    process.exit(1);
  }

  const raw = fs.readFileSync(tourPath, "utf8");
  const doc = yaml.load(raw);
  if (!doc || typeof doc !== "object") {
    console.error("Invalid tour YAML");
    process.exit(1);
  }

  const baseUrl = (doc.base_url || process.env.LENSES_BASE_URL || "http://127.0.0.1:8080").replace(
    /\/$/,
    ""
  );
  const defaults = doc.defaults || {};
  const globalMax = defaults.max_shots_per_folder ?? 20;
  const vp = defaults.viewport || {};
  const viewport = {
    width: Number(vp.width) || 1440,
    height: Number(vp.height) || 900,
  };

  const runId = new Date().toISOString().replace(/[:.]/g, "-");
  const outRoot = args.outDir
    ? path.resolve(args.outDir)
    : path.join(repoRoot, "agents", "workspaces", "studio-explore", runId);

  ensureDir(outRoot);

  const runMdLines = [
    `# Studio explore run`,
    ``,
    ...(doc.title ? [`- **Tour title:** ${doc.title}`] : []),
    `- **When:** ${new Date().toISOString()}`,
    `- **Tour:** \`${tourPath}\``,
    `- **Base URL:** ${baseUrl}`,
    `- **Repo root:** ${repoRoot}`,
    `- **Git:** ${gitHead(repoRoot)}`,
    `- **Viewport:** ${viewport.width}x${viewport.height}`,
    ``,
  ];
  const runMd = runMdLines.join("\n");
  fs.writeFileSync(path.join(outRoot, "RUN.md"), runMd, "utf8");

  const browser = await chromium.launch({
    headless: !args.headed,
    args: args.headed ? [] : ["--no-sandbox", "--disable-dev-shm-usage"],
  });

  try {
    const context = await browser.newContext({ viewport });
    const page = await context.newPage();

    for (const folder of doc.folders || []) {
      const fid = sanitizeFolderId(folder.id || "folder");
      const maxShots = Number(folder.max_shots) || globalMax;
      const steps = folder.steps || [];
      if (steps.length > maxShots) {
        throw new Error(
          `Folder "${fid}" has ${steps.length} steps; max_shots is ${maxShots} (cap ~10–20 per logical folder).`
        );
      }

      const folderDir = resolveFolderDir(outRoot, folder);
      ensureDir(folderDir);

      if (folder.workspace_lens) {
        await applyWorkspaceLens(context, page, baseUrl, folder.workspace_lens);
      }

      const manifest = {
        folder_id: fid,
        folder_title: folder.title || fid,
        directory: folder.directory || fid,
        workspace_lens: folder.workspace_lens || null,
        nav_section: folder.nav_section || null,
        base_url: baseUrl,
        captured_at: new Date().toISOString(),
        viewport,
        steps: [],
      };

      let n = 0;
      let captured = 0;
      for (const step of steps) {
        n += 1;
        const sid = String(step.id || `step-${n}`).replace(/[^a-zA-Z0-9._-]+/g, "_");
        const prefix = `${String(n).padStart(2, "0")}-${sid}`;
        const pngName = `${prefix}.png`;
        const metaName = `${prefix}.meta.json`;
        if (!step.path) {
          throw new Error(`Step ${prefix} missing path`);
        }

        const optional = !!step.optional;
        let finalUrl = "";
        let skipped = false;
        let skipReason = "";
        try {
          finalUrl = await runStep(page, step, baseUrl, viewport);
        } catch (err) {
          if (optional) {
            skipped = true;
            skipReason = err instanceof Error ? err.message : String(err);
            console.warn(`[optional skip] ${sid}: ${skipReason}`);
          } else {
            throw err;
          }
        }

        const meta = {
          id: sid,
          title: step.title || sid,
          path: step.path,
          url: skipped ? "" : finalUrl,
          viewport,
          annotation: step.annotation || "",
          notes: step.notes || "",
          optional,
          skipped,
          ...(skipped ? { error: skipReason } : {}),
        };
        fs.writeFileSync(path.join(folderDir, metaName), JSON.stringify(meta, null, 2), "utf8");

        if (!skipped) {
          const pngPath = path.join(folderDir, pngName);
          await page.screenshot({ path: pngPath, fullPage: !!step.full_page });
          captured += 1;
          manifest.steps.push({
            id: sid,
            title: step.title || sid,
            path: step.path,
            annotation: step.annotation || "",
            screenshot: pngName,
            meta: metaName,
          });
        } else {
          manifest.steps.push({
            id: sid,
            title: step.title || sid,
            path: step.path,
            annotation: step.annotation || "",
            skipped: true,
            error: skipReason,
            screenshot: null,
            meta: metaName,
          });
        }
      }

      fs.writeFileSync(path.join(folderDir, "manifest.json"), JSON.stringify(manifest, null, 2), "utf8");
      console.log(`Wrote ${captured} screenshot(s), ${n - captured} optional skip(s) → ${folderDir}`);
    }
  } finally {
    await browser.close();
  }

  console.log(`Done. Output: ${outRoot}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
