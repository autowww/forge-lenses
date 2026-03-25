# forge-lenses

**forge-lenses** (Python package **lenses**) is a local tool that shows what lives in your development workspace: git repos, orchestration scripts at the workspace root, Firebase-backed site repos, and Blueprint-style WBS files under `docs/requirements/`.

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

When **forge-lenses** is a submodule at **`forge-lenses/`**, run at the **host** repo root:

```bash
./forge-lenses/scripts/lenses-startup.sh
```

This creates:

- **`.lenses-local/`** — gitignored; machine-only.
- **`.lenses-repo/<github-login>/`** — committed (`.gitkeep`); per-user shared files. Login from **`gh api user`**, else **`origin`** on GitHub.

## Workspace root

Resolution order:

1. `--workspace-root` CLI flag  
2. `LENSES_WORKSPACE_ROOT` environment variable  
3. **Heuristic:** parent of the **forge-lenses** checkout, or superproject root when embedded as a submodule  

For a multi-repo folder, set `LENSES_WORKSPACE_ROOT` to that parent.

## External sites

The dashboard links to the published **Handbook** and **Forge** sites; it does not embed them.
