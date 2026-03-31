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
| `lenses/website/` | Markdown source for **reference** handbook pages (merged with `docs/` in `build-lenses-docs.py`) |
| `lenses/fa-tutorial-md/` | Markdown source for **forge-autodoc** tutorials |
| `lenses/tutorials/` | Generated tutorial HTML (gitignored); synced to `tutorial/` at repo root |
| `tutorial/` | Synced tutorial output for `/local-site/<repo>/tutorial/…` (gitignored) |
| `generator/build-lenses-docs.py` | Builds `lenses-docs/` for `/docs/` |
| `build-fa-tutorials.sh` | Builds tutorials via **fa** + rsync to `tutorial/` |
| `fa-handbook.yaml` | forge-autodoc config (paths under `lenses/`) |
| `docs/` | Markdown for `/docs/` hub (`index.md`) + merges with reference build |
| `scripts/setup.sh` | Init nested submodules + optional `lenses-startup.sh` |
| `scripts/lenses-startup.sh` | Host-repo `.lenses-local/` + `.lenses-repo/<github-login>/` |
| `scripts/run-lenses.sh` | Build docs (if `markdown`) + start server |
| `scripts/restart-lenses.sh` | Kill listener on `LENSES_PORT` (default 8080), rebuild docs, start server (sets `LENSES_WORKSPACE_ROOT` to repo parent when unset) |
| `desktop/` | **Electron shell (Phase 1, dev-only)** — spawns `python3 -m lenses` and opens a window (see below) |

## Lenses Studio (experimental)

- **React SPA** at [`/studio/`](http://127.0.0.1:8080/studio/) when the server is running — production build output under `lenses/static/studio/` (Vite + React + TypeScript in **`lenses-enterprise/`**). Chart routes reuse kitchensink **`/__ks/js/forge-data-charts.js`** + **`forge-data-charts.css`** with the same JSON endpoints as Classic **`/overview/charts-api`** and **`/projects/<name>/charts-api`**. **New UI is implemented here first**, then mirrored in Classic (server-rendered); see [`docs/adr-001-lenses-studio-shell.md`](docs/adr-001-lenses-studio-shell.md).
- **Build:** from `lenses-enterprise/`, run `npm install` then `npm run build` (writes into `../lenses/static/studio/`). **Tests:** `npm test` (Vitest). **Iterating on Studio:** start the Python server on **:8080** (`python3 -m lenses` or `./scripts/run-lenses.sh`), open **[http://127.0.0.1:8080/studio/](http://127.0.0.1:8080/studio/)**, and in another terminal run **`npm run watch`** to rebuild the SPA on save—no second HTTP port.
- **Electron:** set `LENSES_STUDIO_UI=1` (or legacy `LENSES_ENTERPRISE_UI=1`) when launching the desktop app to open `/studio/` instead of `/`. **`/enterprise/…`** redirects to **`/studio/…`**. The desktop shell **watches `lenses/static/studio/index.html`** and **reloads the BrowserWindow** when it changes (e.g. after `npm run watch` in `lenses-enterprise/`), so you do not need to restart Electron for each Studio bundle. Rebuild the SPA before any distributable packaging if you changed `lenses-enterprise/`.

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
