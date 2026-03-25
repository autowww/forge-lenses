# lenses

**lenses** is a local tool that shows what lives in your development workspace: git repos, orchestration scripts at the workspace root, Firebase-backed site repos, and Blueprint-style WBS files under `docs/requirements/`.

## How it works

- Run the server on **127.0.0.1:8080** (default).
- Every time you **reload** a dashboard page, lenses **rescans** the workspace — no stale cache in v1.
- **Documentation** (this site) is **pre-generated** with kitchensink `showcase_page` and served under `/docs/`.

## Quick start

From the **lenses** repository root:

```bash
./scripts/setup.sh
pip install markdown
python3 generator/build-lenses-docs.py
./scripts/run-lenses.sh
```

Open [http://127.0.0.1:8080/](http://127.0.0.1:8080/) for the dashboard and use **Docs** in the top bar for this handbook.

## Workspace root

Resolution order:

1. `--workspace-root` CLI flag  
2. `LENSES_WORKSPACE_ROOT` environment variable  
3. **Heuristic:** parent directory of the **lenses** checkout (siblings = other repos), or the superproject root when **lenses** is a **git submodule**

For a multi-repo folder (many siblings), point `LENSES_WORKSPACE_ROOT` at that parent even if **lenses** lives inside one product repo.

## External sites

The dashboard links to the published **Handbook** and **Forge** sites; it does not embed them.
