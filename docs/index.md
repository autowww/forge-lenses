# forge-lenses

**forge-lenses** (Python package **lenses**) is a local tool that shows what lives in your development workspace: git repos, orchestration scripts at the workspace root, Firebase-backed site repos, Blueprint-style WBS files under `docs/requirements/`, and an optional **sticker board** ([`/board`](http://127.0.0.1:8080/board)) for Kanban or freeform notes — **local-only** or **shared** (under **`.lenses-repo/<login>/`** plus a local overlay for private stickers).

Public repository: **github.com/autowww/forge-lenses**.

## How it works

- Run the server on **127.0.0.1:8080** (default).
- Every time you **reload** a dashboard page, lenses **rescans** the workspace — no stale cache in v1.
- **Documentation** (this site) is **pre-generated** with kitchensink `showcase_page` and served under `/docs/`.

## Quick start

From the **forge-lenses** repository root:

```bash
./scripts/setup.sh
pip install markdown
python3 generator/build-lenses-docs.py
./scripts/run-lenses.sh
```

Open [http://127.0.0.1:8080/](http://127.0.0.1:8080/) for the dashboard and use **Docs** in the top bar for this handbook.

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

## Reference (Python package)

These handbook pages are generated from Markdown under **`lenses/website/`** and describe current v1 behavior:

- [Package architecture](architecture.html)
- [HTTP API and routes](http-api-and-routes.html)
- [Workspace scan contract](workspace-scan-contract.html)
- [Registry configuration](registry-configuration.html)
- [Dashboard pages](dashboard-pages.html)
