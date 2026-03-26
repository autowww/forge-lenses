# forge-lenses

Public repo: **`autowww/forge-lenses`** on GitHub — local workspace visualization for **Blueprints** / **ForgeSDLC** development (Python server on **:8080**, dynamic dashboard, ks-built docs under `/docs/`).

- **Dynamic dashboard** — reload to refresh (no server-side cache in v1).
- **Reference docs** — `generator/build-lenses-docs.py` → `lenses-docs/`, served under `/docs/`.
- **Tutorials** — Markdown in `lenses/fa-tutorial-md/`; run `./build-fa-tutorials.sh` (forge-autodoc) → `lenses/tutorials/`, synced to repo-root `tutorial/` for dashboard **Tutorial** links.
- **Not deployed to Firebase.**

The Python package inside this repo is still named **`lenses`** (`python3 -m lenses`).

## Repository layout

| Path | Purpose |
|------|---------|
| `kitchensink/` | Submodule (Forge design system) — docs + tutorial builds |
| `forge-autodoc/` | Submodule (**fa**) — `python3 -m forge_autodoc` for tutorials |
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

## Publishing to GitHub

If `git push` fails with **repository not found**, create the public repo first — see [`lenses/fa-tutorial-md/publish-github.md`](lenses/fa-tutorial-md/publish-github.md).

## Development

- Edit **kitchensink** / **blueprints** in their **standalone** repos; bump submodules here after upstream changes.

**Dashboard (server-rendered HTML).** New full pages: add routing in [`lenses/serve.py`](lenses/serve.py) and HTML builders in [`lenses/render.py`](lenses/render.py) (or a small focused module if `render.py` grows), reusing the kitchensink showcase shell via [`lenses/ks_layout.py`](lenses/ks_layout.py). Targeted async behavior can use `GET`/`POST` under `/api/…` and static JS under [`lenses/static/js/`](lenses/static/js/) (`/__lenses/js/…`); keep default navigation as full HTML responses, not a SPA. After changing **Python** in `lenses/`, restart the server (e.g. [`scripts/restart-lenses.sh`](scripts/restart-lenses.sh)) so the process reloads code.
