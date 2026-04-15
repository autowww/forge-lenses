# forge-lenses

Public repo: **`autowww/forge-lenses`** on GitHub — local workspace visualization for **Blueprints** / **ForgeSDLC** development (Python server on **:8080**, dynamic dashboard, ks-built docs under `/docs/`).

- **Dynamic dashboard** — reload to refresh (no server-side cache in v1).
- **Reference docs** — `generator/build-lenses-docs.py` → `lenses-docs/`, served under `/docs/`.
- **Tutorials** — Markdown in `lenses/fa-tutorial-md/`; run `./build-fa-tutorials.sh` (forge-autodoc) → `lenses/tutorials/`, synced to repo-root `tutorial/` for dashboard **Tutorial** links.
- **Not deployed to Firebase.**

The Python package inside this repo is still named **`lenses`** (`python3 -m lenses`).

**Git / branching (Forge Team tier):** [`docs/GIT-WORKFLOW.md`](docs/GIT-WORKFLOW.md).

## Repository layout

| Path | Purpose |
|------|---------|
| `kitchensink/` | Submodule (Forge design system + **forge-autodoc** at `kitchensink/forge-autodoc`) — docs + tutorial builds |
| `blueprints/` | Submodule (framework source) |
| `lenses/` | Python package (`serve`, `scan`, …) |
| `lenses/website/` | Markdown source for **maintainer** reference pages (merged with `docs/` in `build-lenses-docs.py`) |
| `docs/website/` | User-facing handbook source published on **blueprints.forgesdlc.com/lenses/** (not the full internal `docs/` tree) |
| `lenses/fa-tutorial-md/` | Markdown source for **forge-autodoc** tutorials |
| `lenses/tutorials/` | Generated tutorial HTML (gitignored); synced to `tutorial/` at repo root |
| `tutorial/` | Synced tutorial output for `/local-site/<repo>/tutorial/…` (gitignored) |
| `generator/build-lenses-docs.py` | Builds `lenses-docs/` for `/docs/` |
| `build-fa-tutorials.sh` | Builds tutorials via **fa** + rsync to `tutorial/` |
| `fa-handbook.yaml` | forge-autodoc config (paths under `lenses/`) |
| `docs/` | Internal maintainer handbook (`index.md` hub) + `docs/website/` user guide; see `generator/build-lenses-docs.py` |
| `scripts/setup.sh` | Init nested submodules + optional `lenses-startup.sh` |
| `scripts/lenses-startup.sh` | Host-repo `.lenses-local/` + `.lenses-repo/<github-login>/` |
| `scripts/run-lenses.sh` | Build docs (if `markdown`) + start server |
| `scripts/restart-lenses.sh` | Kill listener on `LENSES_PORT` (default 8080), rebuild docs, start server (sets `LENSES_WORKSPACE_ROOT` to repo parent when unset) |
| `.forge/version-release.json` | Optional manifest for the Blueprints **post-commit** release-notes hook (see **Versioning** under *Lenses Studio*) |
| `desktop/` | **Electron shell (Phase 1, dev-only)** — spawns `python3 -m lenses` and opens a window (see below) |

## Lenses Studio (experimental)

- **React SPA** at [`/studio/`](http://127.0.0.1:8080/studio/) when the server is running — production build output under `lenses/static/studio/` (Vite + React + TypeScript in **`lenses-enterprise/`**). Chart routes reuse kitchensink **`/__ks/js/forge-data-charts.js`** + **`forge-data-charts.css`** with the same JSON endpoints as Classic **`/overview/charts-api`** and **`/projects/<name>/charts-api`**. **New UI is implemented here first**, then mirrored in Classic (server-rendered). **Architecture and KS reuse** are documented in the Kitchen Sink repo: [`docs/design/lenses-studio-shell.md`](../forgesdlc-kitchensink/docs/design/lenses-studio-shell.md) (and [`forge-enterprise-ui.md`](../forgesdlc-kitchensink/docs/design/forge-enterprise-ui.md) for theme packs). See also [`docs/adr-001-lenses-studio-shell.md`](docs/adr-001-lenses-studio-shell.md).
- **Versioning:** Studio uses **semantic versioning** in **`lenses-enterprise/package.json`**. Human-readable history: **`lenses-enterprise/CHANGELOG.md`**. Policy (when to bump major/minor/patch, compatibility with the Python server): **`lenses-enterprise/VERSIONING.md`**; shared release discipline and optional git hook: **`blueprints/sdlc/methodologies/forge/setup/VERSIONING-AND-RELEASES.md`**. After `bash blueprints/sdlc/methodologies/forge/setup/install-version-release-hook.sh`, commits under **`lenses-enterprise/`**, **`lenses/`**, or **`desktop/`** append a **`[Unreleased]`** bullet and **auto-bump `PATCH`** unless you edited **`version`** in that commit; raising **`MAJOR`** or **`MINOR`** finalizes **`[Unreleased]`** into a dated **`[x.y.z]`** section. The built UI shows **version · short git SHA** in the **footer**, with full metadata and doc links under **Settings (gear) → About Forge Studio**.
- **Build:** from `lenses-enterprise/`, run `npm install` then `npm run build` (writes into `../lenses/static/studio/`). **Tests:** `npm test` (Vitest). **Iterating on Studio:** start the Python server on **:8080** (`python3 -m lenses` or `./scripts/run-lenses.sh`), open **[http://127.0.0.1:8080/studio/](http://127.0.0.1:8080/studio/)**, and in another terminal run **`npm run watch`** to rebuild the SPA on save—no second HTTP port. If you use **`npm run dev`** (Vite) or **`vite preview`**, Studio calls **`/api/*` same-origin** and Vite **proxies** those paths to `http://127.0.0.1:8080` (see `lenses-enterprise/vite.config.ts`; change the proxy target if your Lenses port differs). Override with **`VITE_LENSES_API_BASE`** when the SPA is hosted without that proxy. The Python server enables **dev CORS** for common dev origins when bound to loopback.
- **Electron:** set `LENSES_STUDIO_UI=1` (or legacy `LENSES_ENTERPRISE_UI=1`) when launching the desktop app to open `/studio/` instead of `/`. **`/enterprise/…`** redirects to **`/studio/…`**. The desktop shell **watches `lenses/static/studio/index.html`** and **reloads the BrowserWindow** when it changes (e.g. after `npm run watch` in `lenses-enterprise/`), so you do not need to restart Electron for each Studio bundle. Rebuild the SPA before any distributable packaging if you changed `lenses-enterprise/`.
- **Blueprints Wizard (experimental):** enabled **by default** in Studio (routes + sidebar) and on the Python server (`experimental_blueprints_wizard_enabled()` is true unless **`LENSES_EXPERIMENTAL_BLUEPRINTS_WIZARD`** is set to **`0`** / **`false`** / **`no`** / **`off`**). **`GET /api/blueprints/wizard/enabled`** returns `{ ok, enabled }`. To hide the wizard in Studio only, set **`VITE_EXPERIMENTAL_BLUEPRINTS_WIZARD=false`** and rebuild. See **`docs/blueprints/wizard-implementation-plan.md`**.
- **Normative routing spec (blueprints):** [`llm-app-settings-and-routing.md`](../blueprints/sdlc/methodologies/forge/llm-app-settings-and-routing.md) — quality tiers, auto/adaptive routing, refinement downshift (Cynefin-aligned).
- **LLM preferences (Studio):** same form from the header **gear → Preferences** (modal) or full page [`/studio/settings/llm`](http://127.0.0.1:8080/studio/settings/llm) — listed under **Workspace** in the sidebar (not Knowledge). **Advanced model options** unlocks autoselection, tier (slider: left = lighter cost, right = deeper analysis), adaptive routing, refinement downshift, and optional **classifier model** overrides (`classifier_models` in JSON). With advanced off, set a single **model id** per active provider. Settings file: **`<workspace>/.lenses-local/llm-settings.json`** (gitignored). Keys in the file override env per provider when non-empty. **API:** `GET /api/llm/settings` (masked keys), `POST /api/llm/settings` with `{ "settings": { ... } }`. **`GET /api/llm/diagnostics`** returns a single JSON bundle for AI Setup: per-provider reachability, credential/base hints, last successful chat time, last Discover/Health probe, token totals, recent failures, routing/fallback events, first-run wizard hints, and file path hints. **`POST /api/llm/provider-probe`** with `{ "provider": "openai"|"anthropic"|"gemini"|"openai_compatible"|"ollama", "action": "models"|"health" }` lists models or a short health signal using **server-side** credentials (never returns raw keys); each call also appends one row to **`probe_log`** in **`llm-usage.json`** for the workspace. For **`openai_compatible`** only, optional **`probe_openai_compatible_base_url`** and **`probe_openai_compatible_bearer`** in the JSON body let Studio **Discover models** / **Test connection** use a draft URL or token before save. **`GET /api/llm/ollama-status`** returns reachability, configured `OLLAMA_BASE_URL`, tag list, **`model_catalog`** (name, size, digest, modified time), and per-tag **`last_used`** timestamps merged from **`<workspace>/.lenses-local/llm-usage.json`**. **`POST /api/llm/ollama-action`** with `{ "action": "pull"|"update"|"delete"|"remove", "model": "<ollama tag>" }` drives Ollama’s HTTP pull/delete (same loopback / `LENSES_ALLOW_ACTIONS` gate as other LLM APIs). **`GET /api/llm/routing-preview`** and **`POST /api/llm/routing-preview-draft`** (body `{ "settings": { … } }`, merged in memory only) return per-task effective routes for AI Setup, including **`routing_mode`**, **`explanation`**, **`privacy`**, **`fallback_provider` / `fallback_model`**, and **`privacy_warn`** when local-only cannot be satisfied.
- **LLM chat (demo):** [`/studio/chat`](http://127.0.0.1:8080/studio/chat) — server-side proxy; resolves model from env + preferences (tier ladder, optional adaptive classifier for OpenAI/Gemini, refinement downshift when `refine: true`). **If you see HTTP 404 on `/api/...`:** the Studio bundle must reach the Python app (same host with a working `/api` route, Vite proxy in dev, or **`VITE_LENSES_API_BASE`**). **Access:** same as other privileged local APIs: **loopback clients only by default**, or set `LENSES_ALLOW_ACTIONS=1` to allow non-loopback clients (avoid on untrusted networks). Endpoints: `GET /api/llm/providers`, `GET /api/llm/ollama-status`, `POST /api/llm/ollama-action`, `GET /api/llm/usage` (totals, recent events, recent `probe_log`), `GET /api/llm/diagnostics`, `POST /api/llm/chat` with JSON `{ "provider", "message", "model"?, "refine"? }` — responses include `usage` when the provider returns token counts. **Local analytics:** every chat attempt appends to **`<workspace>/.lenses-local/llm-usage.json`** (gitignored): token totals on success, per-event `ok` / error / model / routing / fallback / task id / message length (not content). Optional **`LENSES_LLM_USAGE_MAX_EVENTS`** (default 500, max 10000) caps the rolling `events` array. LLM preferences shows totals, attempts/failures, and a green ✓ when that provider has a recorded successful chat. **Providers:** set at least one of the following as needed:
  - **anthropic** — `ANTHROPIC_API_KEY`; optional `LENSES_ANTHROPIC_MODEL` (default `claude-3-5-haiku-20241022`).
  - **openai** — `OPENAI_API_KEY`; optional `LENSES_OPENAI_MODEL` (default `gpt-4o-mini`).
  - **gemini** — `GOOGLE_API_KEY` or `GEMINI_API_KEY`; optional `LENSES_GEMINI_MODEL` (default `gemini-2.0-flash`).
  - **ollama** — local [Ollama](https://ollama.com) HTTP API; optional `OLLAMA_BASE_URL` (default `http://127.0.0.1:11434`), optional `LENSES_OLLAMA_MODEL` (default `llama3.2`). **Connection refused / Errno 111:** the Ollama app or `ollama serve` is not running on that URL, or use a different `OLLAMA_BASE_URL`. **One-shot helper:** [`scripts/setup-ollama-for-lenses.sh`](scripts/setup-ollama-for-lenses.sh) installs (optional `OLLAMA_AUTO_INSTALL=1`), starts `ollama serve` if needed, and runs `ollama pull` for `LENSES_OLLAMA_MODEL`. The same script is embedded in **AI Setup → Local models (Ollama)** (install/start/connect) and still appears from **Try Chat** when **ollama** is selected.
  - **openai_compatible** — `LENSES_OPENAI_COMPAT_BASE_URL` (e.g. LM Studio) or **`openai_compatible_base_url`** in **`llm-settings.json`** (file wins over env when non-empty); optional `LENSES_OPENAI_COMPAT_KEY`, `LENSES_OPENAI_COMPAT_MODEL`.

## Desktop app (Electron, Phase 1, dev-only)

Prerequisites: **Node.js** (LTS), **`python3`** on `PATH`, and Python deps from the repo root (`pip install -r requirements.txt` or your venv). The shell does **not** bundle Python; it runs the same code as `scripts/run-lenses.sh`. The server listens on **127.0.0.1** on a **free port** (not necessarily `8080`), so it will not collide with an existing CLI session on `:8080`.

**Workspace selection** (what Lenses scans as sibling repos):

1. **`LENSES_WORKSPACE_ROOT`** in the environment (highest precedence; must exist and be a directory).
2. Else **`lenses-desktop.json`** in the **current working directory** when the app starts (the folder you `cd` into before `npm start`). Shape: `{ "workspaceRoot": "/absolute/path/to/workspace" }`.
3. Else a **folder picker** runs on startup; the chosen path is saved to **`lenses-desktop.json`** in that same working directory.

If you cancel the picker, the app exits. Because the config file is tied to **`process.cwd()`**, always start from the same directory if you want a stable saved workspace, or set **`LENSES_WORKSPACE_ROOT`** instead.

```bash
cd desktop
npm install
LENSES_STUDIO_UI=1 npm start
```

With **`LENSES_STUDIO_UI=1`**, saving Studio sources while **`npm run watch`** runs in `lenses-enterprise/` updates `lenses/static/studio/index.html`; the Electron window reloads when that file changes.

Reference docs under `/docs/` are empty until you run `python3 generator/build-lenses-docs.py` from the repo root (same as the CLI). Override the Python executable with **`PYTHON`** if needed (e.g. Windows or a venv path).

On some Linux setups, Electron’s sandbox may require `--no-sandbox` (already added to the `npm start` script in this repo). If your environment is fully configured for Chromium’s setuid sandbox, you can run `electron .` without that flag from `desktop/`.

**Ubuntu (GNOME) app menu:** from `desktop/`, run `./install-ubuntu-launchers.sh` to install **Forge Lenses** and **Forge Studio** entries under `~/.local/share/applications/` (search the app grid or Activities). Run again after moving the repo clone. Remove with `./install-ubuntu-launchers.sh --remove`.

## Quick start (standalone clone)

```bash
git clone https://github.com/autowww/forge-lenses.git
cd forge-lenses
./scripts/setup.sh
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python3 generator/build-lenses-docs.py
./build-fa-tutorials.sh
./scripts/run-lenses.sh
# or, to replace an already-running instance on :8080:
# ./scripts/restart-lenses.sh
```

Open [http://127.0.0.1:8080/](http://127.0.0.1:8080/) · JSON: [http://127.0.0.1:8080/api/workspace-state](http://127.0.0.1:8080/api/workspace-state)

## Submodule in another project

```bash
git submodule add https://github.com/autowww/forge-lenses.git forge-lenses
git submodule update --init --recursive
./forge-lenses/scripts/lenses-startup.sh
```

`lenses-startup.sh` creates **`.lenses-local/`** (gitignored) and **`.lenses-repo/<your-github-login>/`** (tracked, with `.gitkeep` and a short `README.txt` if missing) at the **host product repo root**, not inside `forge-lenses/`, when **forge-lenses** is a submodule (it detects the git superproject). On a **standalone** forge-lenses clone, those dirs stay at the forge-lenses root by default. Login from `gh api user` or the **`origin` URL of the resolved git repo** (the host or forge-lenses checkout).

Then from **`forge-lenses/`**: `./scripts/setup.sh` for nested submodules.

Set **`LENSES_WORKSPACE_ROOT`** to your **multi-repo parent folder** (the directory that contains `forge-lenses/` and sibling project checkouts) when you want the dashboard to scan siblings **and** when you want **`.lenses-local/`** / **`.lenses-repo/`** on that parent instead of inside the forge-lenses git root. Example:

```bash
export LENSES_WORKSPACE_ROOT=/path/to/your/Code
./scripts/setup.sh
# or: LENSES_WORKSPACE_ROOT=/path/to/your/Code ./scripts/lenses-startup.sh
```

## Host repo data directories

These paths are created on the **repository that owns the product** (the superproject when **forge-lenses** is embedded), not under `forge-lenses/` itself.

| Path | Committed? | Purpose |
|------|------------|---------|
| `.lenses-local/` | No | Machine-only caches, notes, local config |
| `.lenses-repo/<github-login>/` | Yes | Commit-friendly “shared with the repo” area (per-contributor slot); not named `.lenses-shared` |

## Configuration

Copy `workspace-registry.example.json` to `workspace-registry.json` in **forge-lenses** to override handbook/forge URLs and ignore paths.

## Releases and versioning

**forge-lenses** is consumed by **cloning**, **git submodule**, or **forking** — there is no separate installer artifact in this repo yet (see **Desktop app** above for the current Electron scope).

| Need | What to do |
|------|------------|
| **Pin a known-good revision** | Use an **annotated tag** on `main` (e.g. `v0.4.0`). In a standalone clone: `git fetch --tags && git checkout v0.4.0`. In a **submodule**: `cd forge-lenses && git fetch --tags && git checkout v0.4.0`, then commit the updated submodule pointer in the **host** repo. |
| **Track latest** | `git pull` on `main` (standalone) or `git submodule update --remote forge-lenses` from the superproject when you intentionally want to advance. |
| **Release notes** | Optionally create a **[GitHub Release](https://github.com/autowww/forge-lenses/releases)** for each tag — even without binary attachments — so adopters see changelog-style notes and compare versions. |

**Handbook site:** [blueprints-website](https://github.com/autowww/blueprints-website) vendors **forge-lenses** as a submodule to build static **`website/lenses/`**. Bump that submodule when you want the published handbook to match a specific **forge-lenses** commit (same workflow as other submodules).

**Blueprint quickstart:** [Forge Studio quickstart](https://github.com/autowww/blueprints/blob/main/sdlc/quickstarts/forge-studio.md) (clone/submodule, run server, `/studio/`).

## Publishing to GitHub

If `git push` fails with **repository not found**, create the public repo first — see [`lenses/fa-tutorial-md/publish-github.md`](lenses/fa-tutorial-md/publish-github.md).

## Development

- Edit **kitchensink** / **blueprints** in their **standalone** repos; bump submodules here after upstream changes.

**Dashboard (server-rendered HTML).** New full pages: add routing in [`lenses/serve.py`](lenses/serve.py) and HTML builders in [`lenses/render.py`](lenses/render.py) (or a small focused module if `render.py` grows), reusing the kitchensink showcase shell via [`lenses/ks_layout.py`](lenses/ks_layout.py). Targeted async behavior can use `GET`/`POST` under `/api/…` and static JS under [`lenses/static/js/`](lenses/static/js/) (`/__lenses/js/…`); keep default navigation as full HTML responses, not a SPA. After changing **Python** in `lenses/`, restart the server (e.g. [`scripts/restart-lenses.sh`](scripts/restart-lenses.sh)) so the process reloads code.
