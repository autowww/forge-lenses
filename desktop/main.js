/**
 * Phase 1 Electron shell: spawn `python3 -m lenses` with the same env defaults as
 * scripts/run-lenses.sh, then load the dashboard in a BrowserWindow.
 */
const { app, BrowserWindow, dialog, Menu, ipcMain } = require("electron");
const { spawn, execSync } = require("child_process");
const path = require("path");
const fsSync = require("fs");
const fs = require("fs/promises");
const net = require("net");
const http = require("http");

const REPO_ROOT = path.join(__dirname, "..");

/**
 * Studio bundle identity for the Electron splash: prefers `studio-build-meta.json`
 * written beside `index.html` on `npm run build` in `lenses-enterprise/` (semver +
 * commit + UTC build time). Falls back to `package.json` + git when the file is missing.
 * @returns {{ version: string, commit: string, buildTime: string }}
 */
function lensesEnterpriseBuildMeta() {
  const metaPath = path.join(
    REPO_ROOT,
    "lenses",
    "static",
    "studio",
    "studio-build-meta.json",
  );
  try {
    const raw = fsSync.readFileSync(metaPath, "utf8");
    const j = JSON.parse(raw);
    if (
      j &&
      typeof j.studioVersion === "string" &&
      typeof j.studioBuildCommit === "string" &&
      typeof j.studioBuildTime === "string"
    ) {
      return {
        version: j.studioVersion,
        commit: j.studioBuildCommit,
        buildTime: j.studioBuildTime,
      };
    }
  } catch (_) {
    /* not built yet or invalid JSON */
  }
  const pkgPath = path.join(REPO_ROOT, "lenses-enterprise", "package.json");
  let version = "";
  try {
    const pkg = JSON.parse(fsSync.readFileSync(pkgPath, "utf8"));
    if (typeof pkg.version === "string") version = pkg.version;
  } catch (_) {
    /* missing or invalid package.json */
  }
  let commit = "";
  try {
    commit = execSync("git rev-parse --short HEAD", {
      cwd: path.join(REPO_ROOT, "lenses-enterprise"),
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    }).trim();
  } catch (_) {
    /* shallow clone or git unavailable */
  }
  return { version, commit, buildTime: "" };
}

function virtualCameraStudioFromEnv() {
  return (
    process.env.LENSES_VIRTUAL_CAMERA_STUDIO === "1" ||
    process.env.LENSES_VIRTUAL_CAMERA_STUDIO === "true"
  );
}

function studioUiFromEnv() {
  return (
    virtualCameraStudioFromEnv() ||
    process.env.LENSES_STUDIO_UI === "1" ||
    process.env.LENSES_STUDIO_UI === "true" ||
    process.env.LENSES_ENTERPRISE_UI === "1" ||
    process.env.LENSES_ENTERPRISE_UI === "true"
  );
}

function productDisplayName() {
  if (virtualCameraStudioFromEnv()) return "Virtual Camera Studio";
  if (
    process.env.LENSES_STUDIO_UI === "1" ||
    process.env.LENSES_STUDIO_UI === "true" ||
    process.env.LENSES_ENTERPRISE_UI === "1" ||
    process.env.LENSES_ENTERPRISE_UI === "true"
  ) {
    return "Forge Studio";
  }
  return "Forge Lenses";
}

/** Client-side route under `/studio` basename (leading slash). */
function studioInitialSubpath() {
  if (virtualCameraStudioFromEnv()) return "/labs/virtual-camera";
  const raw = (process.env.LENSES_STUDIO_INITIAL_PATH || "").trim();
  if (!raw) return "";
  if (raw.startsWith("/")) return raw.replace(/\/+$/, "") || "";
  return "/" + raw.replace(/^\/+/, "");
}

/** @param {number} port */
function studioDashboardUrl(port) {
  const base = `http://127.0.0.1:${port}/studio`;
  const sub = studioInitialSubpath();
  if (!sub) return `${base}/`;
  return `${base}${sub}`;
}

/** @param {string} base */
function isLoopbackStickerboardBase(base) {
  const b = String(base || "").trim().toLowerCase();
  if (!b) return true;
  return b.includes("127.0.0.1") || b.includes("://localhost");
}

/**
 * @param {string} filePath
 * @returns {Record<string, string>}
 */
function readDotEnvFile(filePath) {
  /** @type {Record<string, string>} */
  const out = {};
  try {
    for (const line of fsSync.readFileSync(filePath, "utf8").split("\n")) {
      const chunk = line.trim();
      if (!chunk || chunk.startsWith("#") || !chunk.includes("=")) continue;
      const eq = chunk.indexOf("=");
      const key = chunk.slice(0, eq).trim();
      let val = chunk.slice(eq + 1).trim();
      if (
        (val.startsWith('"') && val.endsWith('"')) ||
        (val.startsWith("'") && val.endsWith("'"))
      ) {
        val = val.slice(1, -1);
      }
      if (key) out[key] = val;
    }
  } catch (_) {
    /* missing */
  }
  return out;
}

/**
 * Public guest URL base for copy links (non-loopback when configured).
 * @param {string} workspaceRoot
 * @returns {string}
 */
function resolveStickerboardPublicBase(workspaceRoot) {
  const fromShell = (process.env.LENSES_STICKERBOARD_PUBLIC_BASE || "").trim();
  if (fromShell && !isLoopbackStickerboardBase(fromShell)) {
    return fromShell.replace(/\/$/, "");
  }
  const wsEnv = readDotEnvFile(
    path.join(workspaceRoot, ".lenses-local", "stickerboard-public.env"),
  );
  const wsBase = (wsEnv.LENSES_STICKERBOARD_PUBLIC_BASE || "").trim();
  if (wsBase && !isLoopbackStickerboardBase(wsBase)) {
    return wsBase.replace(/\/$/, "");
  }
  for (const rel of [".env.local", ".env.development", ".env"]) {
    const ent = readDotEnvFile(path.join(REPO_ROOT, "lenses-enterprise", rel));
    const vite = (ent.VITE_STICKERBOARD_PUBLIC_BASE || "").trim();
    if (vite && !isLoopbackStickerboardBase(vite)) {
      return vite.replace(/\/$/, "");
    }
  }
  if (fromShell) return fromShell.replace(/\/$/, "");
  return "http://127.0.0.1:9999";
}

function appIconPath() {
  const name = studioUiFromEnv() ? "forge-studio.png" : "forge-lenses.png";
  return path.join(__dirname, "icons", name);
}

/** Workspace path persisted next to the process cwd when using the folder picker. */
const CONFIG_FILENAME = "lenses-desktop.json";

function configFilePath() {
  return path.join(process.cwd(), CONFIG_FILENAME);
}

/** @type {import('child_process').ChildProcess | null} */
let pythonChild = null;
/** @type {BrowserWindow | null} */
let mainWindow = null;
/** When true, UI attached to an already-running Lenses process (Electron did not spawn Python). */
let attachedToExistingServer = false;

/** @type {BrowserWindow | null} */
let splashWindow = null;
/** @type {number | null} */
let splashVisibleAt = null;
/** @type {ReturnType<typeof setTimeout> | null} */
let splashRevealTimer = null;
/** @type {ReturnType<typeof setInterval> | null} */
let splashWaitInterval = null;

/** Minimum time the splash stays visible (ms), then the main window appears. */
function splashMinVisibleMs() {
  return virtualCameraStudioFromEnv() ? 400 : SPLASH_MIN_VISIBLE_MS;
}

const SPLASH_MIN_VISIBLE_MS = 2000;

let intentionalShutdown = false;

/** Register IPC once — duplicate `ipcMain.handle` for the same channel throws. */
let windowIpcRegistered = false;
function ensureWindowIpcHandlers() {
  if (windowIpcRegistered) {
    return;
  }
  windowIpcRegistered = true;
  ipcMain.handle("win-minimize", () => {
    if (mainWindow && !mainWindow.isDestroyed()) mainWindow.minimize();
  });
  ipcMain.handle("win-maximize", () => {
    if (!mainWindow || mainWindow.isDestroyed()) return;
    if (mainWindow.isMaximized()) mainWindow.unmaximize();
    else mainWindow.maximize();
  });
  ipcMain.handle("win-close", () => {
    if (mainWindow && !mainWindow.isDestroyed()) mainWindow.close();
  });
  ipcMain.handle("win-is-maximized", () =>
    mainWindow && !mainWindow.isDestroyed() ? mainWindow.isMaximized() : false
  );
}

function clearSplashWaitInterval() {
  if (splashWaitInterval) {
    clearInterval(splashWaitInterval);
    splashWaitInterval = null;
  }
}

function closeSplashWindow() {
  clearSplashWaitInterval();
  if (splashRevealTimer) {
    clearTimeout(splashRevealTimer);
    splashRevealTimer = null;
  }
  if (splashWindow && !splashWindow.isDestroyed()) {
    splashWindow.close();
  }
  splashWindow = null;
  splashVisibleAt = null;
}

function whenSplashDomReady() {
  return new Promise((resolve) => {
    if (!splashWindow || splashWindow.isDestroyed()) {
      resolve();
      return;
    }
    const wc = splashWindow.webContents;
    if (wc.isLoading()) {
      wc.once("did-finish-load", () => resolve());
    } else {
      resolve();
    }
  });
}

/**
 * @param {string} main
 * @param {string} [detail]
 * @returns {Promise<void>}
 */
function setSplashPhase(main, detail) {
  const w = splashWindow;
  if (!w || w.isDestroyed()) {
    return Promise.resolve();
  }
  const m = JSON.stringify(main ?? "");
  const d = JSON.stringify(detail ?? "");
  return w.webContents
    .executeJavaScript(`window.__splashSet && window.__splashSet(${m}, ${d})`)
    .catch(() => {});
}

/**
 * Small frameless window while the Python server starts and the main URL loads.
 */
function openSplashWindow() {
  closeSplashWindow();
  const win = new BrowserWindow({
    width: 420,
    height: 276,
    frame: false,
    resizable: false,
    minimizable: false,
    maximizable: false,
    fullscreenable: false,
    show: false,
    center: true,
    icon: appIconPath(),
    title: productDisplayName(),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
  });
  const variant = virtualCameraStudioFromEnv()
    ? "virtual-camera"
    : studioUiFromEnv()
      ? "studio"
      : "lenses";
  const meta = lensesEnterpriseBuildMeta();
  /** @type {Record<string, string>} */
  const query = { variant };
  if (meta.version) query.v = meta.version;
  if (meta.commit) query.c = meta.commit;
  if (meta.buildTime) query.t = meta.buildTime;
  win.loadFile(path.join(__dirname, "splash.html"), {
    query,
  });
  win.once("ready-to-show", () => {
    if (!win.isDestroyed()) {
      win.show();
      splashVisibleAt = Date.now();
    }
  });
  splashWindow = win;
  return win;
}

/** @type {ReturnType<typeof setTimeout> | null} */
let studioIndexReloadTimer = null;

/**
 * When Lenses Studio is open, reload the window after `index.html` changes (e.g. `npm run watch`
 * in `lenses-enterprise/`). Avoids reloading on every hashed asset write.
 */
function watchStudioIndexForReload() {
  const studioDir = path.join(REPO_ROOT, "lenses", "static", "studio");
  try {
    if (!fsSync.existsSync(studioDir)) {
      fsSync.mkdirSync(studioDir, { recursive: true });
    }
    fsSync.watch(studioDir, { persistent: true }, (event, filename) => {
      if (filename !== "index.html") {
        return;
      }
      if (studioIndexReloadTimer) {
        clearTimeout(studioIndexReloadTimer);
      }
      studioIndexReloadTimer = setTimeout(() => {
        studioIndexReloadTimer = null;
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.reloadIgnoringCache();
        }
      }, 450);
    });
  } catch (err) {
    console.warn("[lenses-desktop] could not watch Studio bundle:", err.message);
  }
}

function pythonExecutable() {
  if (process.env.PYTHON) {
    return process.env.PYTHON;
  }
  return process.platform === "win32" ? "python" : "python3";
}

/**
 * @returns {Promise<string | null>} Absolute workspace root, or null if user cancelled / error.
 */
async function loadWorkspaceFromConfig() {
  const p = configFilePath();
  let raw;
  try {
    raw = await fs.readFile(p, "utf8");
  } catch (err) {
    if (err && typeof err === "object" && "code" in err && err.code === "ENOENT") {
      return null;
    }
    throw err;
  }
  let data;
  try {
    data = JSON.parse(raw);
  } catch {
    return null;
  }
  const wr =
    data && typeof data.workspaceRoot === "string" ? data.workspaceRoot.trim() : "";
  if (!wr) {
    return null;
  }
  const resolved = path.resolve(wr);
  try {
    const st = await fs.stat(resolved);
    if (!st.isDirectory()) {
      return null;
    }
  } catch {
    return null;
  }
  return resolved;
}

/**
 * @param {string} workspaceDir
 */
async function saveWorkspaceConfig(workspaceDir) {
  const resolved = path.resolve(workspaceDir);
  const payload = { workspaceRoot: resolved };
  await fs.writeFile(
    configFilePath(),
    `${JSON.stringify(payload, null, 2)}\n`,
    "utf8"
  );
}

/**
 * Precedence: LENSES_WORKSPACE_ROOT env → lenses-desktop.json in process.cwd() → folder dialog.
 * @returns {Promise<string | null>}
 */
async function resolveWorkspaceRoot() {
  const env = process.env.LENSES_WORKSPACE_ROOT;
  if (env && env.trim()) {
    const resolved = path.resolve(env.trim());
    try {
      const st = await fs.stat(resolved);
      if (!st.isDirectory()) {
        dialog.showErrorBox(
          "Invalid workspace",
          `LENSES_WORKSPACE_ROOT is not a directory:\n${resolved}`
        );
        return null;
      }
      return resolved;
    } catch {
      dialog.showErrorBox(
        "Invalid workspace",
        `LENSES_WORKSPACE_ROOT path does not exist:\n${resolved}`
      );
      return null;
    }
  }

  const fromFile = await loadWorkspaceFromConfig();
  if (fromFile) {
    return fromFile;
  }

  const result = await dialog.showOpenDialog({
    title: "Choose Lenses workspace root",
    message:
      "Select the folder that contains forge-lenses and your sibling project checkouts.",
    properties: ["openDirectory"],
  });

  if (result.canceled || !result.filePaths || result.filePaths.length === 0) {
    dialog.showMessageBoxSync({
      type: "info",
      title: "Lenses",
      message: "No workspace folder selected. Lenses will exit.",
    });
    return null;
  }

  const chosen = result.filePaths[0];
  try {
    await saveWorkspaceConfig(chosen);
  } catch (err) {
    dialog.showErrorBox(
      "Could not save config",
      `Could not write ${configFilePath()}:\n${
        err instanceof Error ? err.message : String(err)
      }`
    );
    return null;
  }

  return path.resolve(chosen);
}

/** Default `python3 -m lenses` port (matches CLI). Full Studio uses this. */
const DEFAULT_LENSES_PORT = 8080;
/** Virtual Camera Studio runs its own Lenses instance so it does not share :8080 with Forge Studio. */
const DEFAULT_VIRTUAL_CAMERA_STUDIO_PORT = 8096;

/**
 * @returns {number}
 */
function studioLensesPort() {
  const raw = process.env.LENSES_PORT;
  const envPort = raw && String(raw).trim() ? parseInt(String(raw).trim(), 10) : NaN;
  if (Number.isFinite(envPort) && envPort > 0 && envPort < 65536) {
    return envPort;
  }
  if (virtualCameraStudioFromEnv()) {
    return DEFAULT_VIRTUAL_CAMERA_STUDIO_PORT;
  }
  return DEFAULT_LENSES_PORT;
}

/**
 * @param {number} port
 * @returns {Promise<boolean>}
 */
function isTcpPortFree(port) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.once("error", () => resolve(false));
    server.listen(port, "127.0.0.1", () => {
      server.close(() => resolve(true));
    });
  });
}

/**
 * @param {number} port
 * @param {string} expectedWorkspaceRoot
 * @returns {Promise<boolean>}
 */
/**
 * Free TCP listeners on loopback so Studio can bind the fixed Lenses port.
 * @param {number} port
 */
function killListenersOnPort(port) {
  const p = Number(port);
  if (!Number.isFinite(p) || p <= 0 || p >= 65536) {
    return;
  }
  if (process.platform === "win32") {
    try {
      const out = execSync(`netstat -ano | findstr :${p}`, {
        encoding: "utf8",
        stdio: ["ignore", "pipe", "ignore"],
      });
      const pids = new Set();
      for (const line of out.split("\n")) {
        const m = line.trim().match(/\s+(\d+)\s*$/);
        if (m) pids.add(m[1]);
      }
      for (const pid of pids) {
        try {
          execSync(`taskkill /PID ${pid} /F`, { stdio: "ignore" });
        } catch (_) {
          /* ignore */
        }
      }
    } catch (_) {
      /* nothing listening */
    }
    return;
  }
  try {
    execSync(`fuser -k ${p}/tcp`, { stdio: "ignore", timeout: 8000 });
  } catch (_) {
    try {
      const out = execSync(`ss -lptn 'sport = :${p}'`, {
        encoding: "utf8",
        stdio: ["ignore", "pipe", "ignore"],
        timeout: 3000,
      });
      const seen = new Set();
      for (const m of out.matchAll(/pid=(\d+)/g)) {
        const pid = Number(m[1]);
        if (!pid || seen.has(pid)) continue;
        seen.add(pid);
        try {
          process.kill(pid, "SIGTERM");
        } catch (_) {
          /* ignore */
        }
      }
    } catch (_) {
      /* ignore */
    }
  }
}

/**
 * @param {number} port
 * @param {number} [timeoutMs]
 * @returns {Promise<boolean>}
 */
async function waitForTcpPortFree(port, timeoutMs = 10_000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    if (await isTcpPortFree(port)) {
      return true;
    }
    await new Promise((r) => setTimeout(r, 250));
  }
  return isTcpPortFree(port);
}

function probeExistingLensesServer(port, expectedWorkspaceRoot) {
  const url = `http://127.0.0.1:${port}/api/workspace-state`;
  return new Promise((resolve) => {
    const req = http.get(url, { timeout: 8000 }, (res) => {
      const chunks = [];
      res.on("data", (c) => chunks.push(c));
      res.on("end", () => {
        if (res.statusCode !== 200) {
          resolve(false);
          return;
        }
        try {
          const data = JSON.parse(Buffer.concat(chunks).toString("utf8"));
          const wr =
            data && typeof data.workspace_root === "string" ? data.workspace_root.trim() : "";
          if (!wr) {
            resolve(false);
            return;
          }
          resolve(path.resolve(wr) === path.resolve(expectedWorkspaceRoot));
        } catch {
          resolve(false);
        }
      });
    });
    req.on("error", () => resolve(false));
    req.on("timeout", () => {
      req.destroy();
      resolve(false);
    });
  });
}

/**
 * Studio uses a fixed loopback port per shell (8080 Forge Studio, 8096 Virtual Camera Studio).
 * Reuse Lenses when the workspace matches; otherwise kill whatever holds the port and spawn fresh.
 * @param {string} workspaceRoot
 * @returns {Promise<{ attach: boolean; port: number }>}
 */
async function resolvePortAndAttachMode(workspaceRoot) {
  const wr = path.resolve(workspaceRoot);
  const port = studioLensesPort();

  if (await probeExistingLensesServer(port, wr)) {
    return { attach: true, port };
  }

  if (!(await isTcpPortFree(port))) {
    killListenersOnPort(port);
    await waitForTcpPortFree(port);
  }

  return { attach: false, port };
}

/**
 * @param {number} port
 * @param {number} timeoutMs
 */
function waitForHttpRoot(port, timeoutMs = 90_000) {
  const url = `http://127.0.0.1:${port}/`;
  const start = Date.now();
  return new Promise((resolve, reject) => {
    function attempt() {
      const req = http.get(url, (res) => {
        res.resume();
        if (res.statusCode && res.statusCode >= 200 && res.statusCode < 500) {
          resolve();
        } else if (Date.now() - start > timeoutMs) {
          reject(new Error(`GET / returned ${res.statusCode}; giving up`));
        } else {
          setTimeout(attempt, 150);
        }
      });
      req.on("error", () => {
        if (Date.now() - start > timeoutMs) {
          reject(new Error("Lenses server did not respond on GET / in time"));
        } else {
          setTimeout(attempt, 150);
        }
      });
    }
    attempt();
  });
}

function killPythonChild() {
  if (attachedToExistingServer || !pythonChild || pythonChild.killed) {
    return;
  }
  try {
    pythonChild.kill("SIGTERM");
  } catch {
    /* ignore */
  }
  const childRef = pythonChild;
  const t = setTimeout(() => {
    if (childRef && !childRef.killed) {
      try {
        childRef.kill("SIGKILL");
      } catch {
        /* ignore */
      }
    }
  }, 2500);
  if (typeof t.unref === "function") {
    t.unref();
  }
}

async function startLensesAndShowWindow() {
  ensureWindowIpcHandlers();

  const workspaceRoot = await resolveWorkspaceRoot();
  if (workspaceRoot == null) {
    intentionalShutdown = true;
    app.quit();
    return;
  }

  attachedToExistingServer = false;

  openSplashWindow();
  await whenSplashDomReady();
  await setSplashPhase(
    "Preparing connection…",
    virtualCameraStudioFromEnv()
      ? `Virtual Camera Studio uses 127.0.0.1:${studioLensesPort()} only (not Forge Studio on :8080).`
      : `Studio uses 127.0.0.1:${studioLensesPort()} only. Reuse Lenses when the workspace matches; otherwise the process on that port is stopped and Python is started. Search FTS indexing runs in the background after a new server starts.`,
  );

  const { attach, port } = await resolvePortAndAttachMode(workspaceRoot);
  attachedToExistingServer = attach;

  const exe = pythonExecutable();

  if (attach) {
    await setSplashPhase(
      "Using an existing Lenses server…",
      `http://127.0.0.1:${port}/ — workspace matches; Electron will not start a second Python process.`
    );
  } else {
    await setSplashPhase(
      "Starting the Lenses server (Python)…",
      `${exe} -m lenses — 127.0.0.1:${port} · LENSES_SEARCH_REINDEX_ON_START=1 (HTML/Markdown search index in background)`
    );

    const stickerboardPublicBase = resolveStickerboardPublicBase(workspaceRoot);
    const vcOnly = virtualCameraStudioFromEnv();
    const env = {
      ...process.env,
      PYTHONPATH: REPO_ROOT,
      LENSES_WORKSPACE_ROOT: workspaceRoot,
      LENSES_PORT: String(port),
      LENSES_SEARCH_REINDEX_ON_START: vcOnly
        ? "0"
        : process.env.LENSES_SEARCH_REINDEX_ON_START ?? "1",
      LENSES_STICKERBOARD_PUBLIC_BASE: stickerboardPublicBase,
      LENSES_STICKERBOARD_PORT: vcOnly
        ? "0"
        : process.env.LENSES_STICKERBOARD_PORT ?? "9999",
      LENSES_STICKERBOARD_LOOPBACK_DEV_AUTH:
        process.env.LENSES_STICKERBOARD_LOOPBACK_DEV_AUTH ?? "1",
      // Blueprints Wizard session APIs + interpret/refine (same LLM stack as Chat). Opt out with LENSES_EXPERIMENTAL_BLUEPRINTS_WIZARD=0 on the shell before launch.
      LENSES_EXPERIMENTAL_BLUEPRINTS_WIZARD: vcOnly
        ? "0"
        : process.env.LENSES_EXPERIMENTAL_BLUEPRINTS_WIZARD ?? "1",
      LENSES_EXPERIMENTAL_ORCHESTRATION_GRAPH: vcOnly
        ? "0"
        : process.env.LENSES_EXPERIMENTAL_ORCHESTRATION_GRAPH ?? "1",
      LENSES_EXPERIMENTAL_AGENTIC_BRIDGE_B3: vcOnly
        ? "0"
        : process.env.LENSES_EXPERIMENTAL_AGENTIC_BRIDGE_B3 ?? "1",
      LENSES_EXPERIMENTAL_FOUNDRY: vcOnly
        ? "0"
        : process.env.LENSES_EXPERIMENTAL_FOUNDRY ?? "1",
      LENSES_EXPERIMENTAL_VIRTUAL_CAMERA:
        process.env.LENSES_EXPERIMENTAL_VIRTUAL_CAMERA ?? "1",
      LENSES_WORKSPACE_SCAN_TIMEOUT_SEC:
        process.env.LENSES_WORKSPACE_SCAN_TIMEOUT_SEC ?? "180",
      LENSES_SCAN_CACHE_SEC: process.env.LENSES_SCAN_CACHE_SEC ?? "120",
      LENSES_OVERVIEW_CACHE_SEC: process.env.LENSES_OVERVIEW_CACHE_SEC ?? "300",
    };
    const oidcFile = readDotEnvFile(
      path.join(workspaceRoot, ".lenses-local", "lenses-oidc.env"),
    );
    for (const [key, val] of Object.entries(oidcFile)) {
      if (val && !env[key]) env[key] = val;
    }

    pythonChild = spawn(
      exe,
      ["-m", "lenses", "--host", "127.0.0.1", "--port", String(port)],
      {
        cwd: REPO_ROOT,
        env,
        shell: false,
        stdio: ["ignore", "pipe", "pipe"],
      }
    );

    pythonChild.stdout?.on("data", (chunk) => {
      process.stdout.write(chunk);
    });
    pythonChild.stderr?.on("data", (chunk) => {
      process.stderr.write(chunk);
    });

    pythonChild.on("error", (err) => {
      intentionalShutdown = true;
      closeSplashWindow();
      dialog.showErrorBox(
        "Could not start lenses",
        `${exe} -m lenses failed to spawn.\n\n${err.message}\n\nSet PYTHON to your Python executable or install Python 3 and ensure it is on PATH.`
      );
      app.quit();
    });

    pythonChild.on("exit", (code, signal) => {
      if (
        !intentionalShutdown &&
        code !== 0 &&
        code !== null &&
        mainWindow &&
        !mainWindow.isDestroyed()
      ) {
        dialog.showErrorBox(
          "Lenses exited",
          `The Python server exited with code ${code}${signal ? ` (signal ${signal})` : ""}.`
        );
      }
      pythonChild = null;
    });
  }

  const httpWaitStart = Date.now();
  if (!attach) {
    await setSplashPhase(
      "Waiting until the server responds…",
      "First launch can include workspace scan plus search indexing. Polling GET http://127.0.0.1:" +
        port +
        "/"
    );
    splashWaitInterval = setInterval(() => {
      const sec = Math.floor((Date.now() - httpWaitStart) / 1000);
      void setSplashPhase(
        "Waiting until the server responds…",
        `${sec}s elapsed — workspace scan, imports, or search FTS · http://127.0.0.1:${port}/`
      );
    }, 2000);
  } else {
    await setSplashPhase(
      "Checking the dashboard…",
      `GET http://127.0.0.1:${port}/`
    );
  }

  try {
    await waitForHttpRoot(port);
  } catch (err) {
    intentionalShutdown = true;
    closeSplashWindow();
    killPythonChild();
    dialog.showErrorBox(
      "Lenses did not start",
      err instanceof Error ? err.message : String(err)
    );
    app.quit();
    return;
  } finally {
    clearSplashWaitInterval();
  }

  await setSplashPhase("Server is up — loading the app…", `Opening the dashboard in the main window.`);

  const useStudio = studioUiFromEnv();
  const vcOnly = virtualCameraStudioFromEnv();
  const dashboardUrl = useStudio
    ? studioDashboardUrl(port)
    : `http://127.0.0.1:${port}/`;

  const preloadPath = path.join(__dirname, "preload.js");
  const winOpts = {
    width: vcOnly ? 1100 : 1280,
    height: vcOnly ? 720 : 840,
    show: false,
    icon: appIconPath(),
    backgroundColor: "#0a0e17",
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: useStudio && fsSync.existsSync(preloadPath) ? preloadPath : undefined,
    },
  };
  if (useStudio) {
    winOpts.frame = false;
  }
  mainWindow = new BrowserWindow(winOpts);

  if (useStudio) {
    const broadcastMax = () => {
      if (!mainWindow || mainWindow.isDestroyed()) return;
      mainWindow.webContents.send(
        "win-maximized-changed",
        mainWindow.isMaximized()
      );
    };
    mainWindow.on("maximize", broadcastMax);
    mainWindow.on("unmaximize", broadcastMax);
    mainWindow.on("enter-full-screen", broadcastMax);
    mainWindow.on("leave-full-screen", broadcastMax);
  }

  mainWindow.once("ready-to-show", () => {
    const showMain = () => {
      if (intentionalShutdown || !mainWindow || mainWindow.isDestroyed()) {
        return;
      }
      closeSplashWindow();
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.show();
        mainWindow.focus();
      }
    };

    const start = splashVisibleAt;
    if (start == null) {
      showMain();
      return;
    }
    const wait = Math.max(0, splashMinVisibleMs() - (Date.now() - start));
    if (wait === 0) {
      showMain();
    } else {
      splashRevealTimer = setTimeout(() => {
        splashRevealTimer = null;
        showMain();
      }, wait);
    }
  });
  mainWindow.loadURL(dashboardUrl);
  if (useStudio) {
    watchStudioIndexForReload();
  }
  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

app.whenReady().then(() => {
  if (virtualCameraStudioFromEnv()) {
    app.setName("Virtual Camera Studio");
  } else if (studioUiFromEnv()) {
    app.setName("Forge Studio");
  } else {
    app.setName("Forge Lenses");
  }
  // Hide the default File/Edit/… menu bar (Linux/Windows).
  Menu.setApplicationMenu(null);
  startLensesAndShowWindow().catch((err) => {
    closeSplashWindow();
    dialog.showErrorBox("Startup failed", err instanceof Error ? err.message : String(err));
    app.quit();
  });
});

app.on("before-quit", () => {
  intentionalShutdown = true;
  closeSplashWindow();
  killPythonChild();
});

app.on("window-all-closed", () => {
  app.quit();
});
