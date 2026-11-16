# forge-lenses

**forge-lenses** (Python package **lenses**) is a local tool that shows what lives in your development workspace: git repos, orchestration scripts at the workspace root, Firebase-backed site repos, Blueprint-style WBS files under `docs/requirements/`, and optional **Forge Stickerboards** ([`/board`](http://127.0.0.1:8080/board)) — multiple Kanban/freeform boards per project, opaque ids on disk — **local-only** or **shared** (under **`.lenses-repo/<login>/sticker-boards/`** plus a local overlay for private stickers on shared boards).

Public repository: **github.com/autowww/forge-lenses**.

## How it works

- Run the server on **127.0.0.1:8080** (default).
- Every time you **reload** a dashboard page, lenses **rescans** the workspace — no stale cache in v1.
- **Reference documentation** is **pre-generated** with kitchensink `showcase_page` and served under **`/docs/`** (build: `python3 generator/build-lenses-docs.py`). **This tutorial** is built with **forge-autodoc** (`handbook_page`) into **`lenses/tutorials/`** and synced to repo-root **`tutorial/`** for the dashboard **Tutorial** link (`./build-fa-tutorials.sh`).

## Quick start

From the **forge-lenses** repository root:

```bash
./scripts/setup.sh
pip install markdown
python3 generator/build-lenses-docs.py
./scripts/run-lenses.sh
```

**Optional — reference page preview images** on the `/docs/` handbook home (`index.html`): `pip install playwright`, run **`playwright install chromium`**, then build with **`--previews`** or set **`LENSES_BUILD_DOC_PREVIEWS=1`**. The generator starts a short-lived local HTTP server on **127.0.0.1** using the first free port in **8090–8200**, captures fixed-viewport PNGs for each page linked under **Reference (Python package)** in **`docs/index.md`**, and writes them under **`lenses-docs/previews/`**. If **playwright** is missing, Chromium is not installed, or no port in that range is free, the docs build still completes; previews are skipped with a message on stderr.

Open [http://127.0.0.1:8080/](http://127.0.0.1:8080/) for the dashboard and use **Docs** in the top bar for the reference handbook.

## Host repo data (submodule consumers)

When **forge-lenses** is a submodule, run **`lenses-startup`** from the host (e.g. `./forge-lenses/scripts/lenses-startup.sh`) or from inside **`forge-lenses/`** — the script **detects the git superproject** and creates data dirs on the **parent product repo root**, not under `forge-lenses/`.

This creates:

- **`.lenses-local/`** — gitignored; machine-only.
- **`.lenses-repo/<github-login>/`** — committed (`.gitkeep`); per-user shared files. Login from **`gh api user`**, else **`origin`** on the **host** repo.

## Workspace root

Resolution order (server scan):

1. `--workspace-root` CLI flag  
2. `LENSES_WORKSPACE_ROOT` environment variable  
3. **Heuristic:** parent of the **forge-lenses** checkout, or superproject root when embedded as a submodule  

For a multi-repo folder, set `LENSES_WORKSPACE_ROOT` to that parent.

**`lenses-startup.sh`** also honors **`LENSES_WORKSPACE_ROOT`**: when set, it creates **`.lenses-local/`** and **`.lenses-repo/`** on that directory instead of only at the git repo root (login still comes from `gh` or **`origin`** on the resolved git checkout).

## External sites

The dashboard links to the published **Handbook** and **Forge** sites in new tabs; it does not embed those production URLs.

## Local site previews

Built static output for Firebase site repos (typically **`website/`**) is served on the same server under **`/local-site/<repo>/…`** (default host **127.0.0.1**). Use **Websites** → **Preview in lenses** for an iframe shell that keeps the dashboard navigation visible.

## Lenses Studio

- [Reference architecture (Lenses Studio)](reference-architecture-studio.md) — React SPA at **`/studio/`**, shared Python **`/api/...`** with Classic, Electron shell, data-plane summary, and links to ADR and the Studio shell API map.

## Reference (Python package)

Maintainer reference pages are generated from **`lenses/website/`** (and internal **`docs/`**) and served under **`/docs/`**. User-facing pages live in **`docs/handbook-public/`** — see the published handbook at **blueprints.forgesdlc.com/lenses/**.

- [Package architecture](/docs/architecture.html)
- [HTTP API and routes](/docs/http-api-and-routes.html)
- [Workspace scan contract](/docs/workspace-scan-contract.html)
- [Registry configuration](/docs/registry-configuration.html)
- [Dashboard pages](/docs/dashboard-pages.html)

For more setup detail see [Setup and submodules](setup.md). For publishing the repo see [Publish forge-lenses on GitHub](publish-github.md).
