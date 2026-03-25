# lenses

Local workspace visualization for development aligned with **Blueprints** and **ForgeSDLC**: see sibling git repos, root-level toolset scripts, Firebase site repos, and WBS files under `docs/requirements/`.

- **Dynamic dashboard** at `http://127.0.0.1:8080/` — reload to refresh (no server-side cache in v1).
- **Documentation** — kitchensink-generated static site under `/docs/` (build with `generator/build-lenses-docs.py`).
- **Not deployed to Firebase** — run on your machine only.

## Repository layout

| Path | Purpose |
|------|---------|
| `kitchensink/` | Submodule (Forge design system) — used to build docs |
| `blueprints/` | Submodule (framework source) — optional reference in checkout |
| `lenses/` | Python package (`serve`, `scan`, …) |
| `generator/build-lenses-docs.py` | Builds `lenses-docs/` from `docs/*.md` |
| `docs/` | Markdown source for lenses documentation |
| `scripts/setup.sh` | Init submodules + checks |
| `scripts/run-lenses.sh` | Build docs (if `markdown` installed) + start server |

## Quick start

```bash
./scripts/setup.sh
# Markdown (for docs build). Prefer: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
pip install -r requirements.txt
python3 generator/build-lenses-docs.py   # optional if run-lenses.sh will run it
./scripts/run-lenses.sh
```

Open the dashboard: [http://127.0.0.1:8080/](http://127.0.0.1:8080/)  
JSON API: [http://127.0.0.1:8080/api/workspace-state](http://127.0.0.1:8080/api/workspace-state)

## Submodule in another project

```bash
git submodule add <url-to-lenses> lenses
cd lenses && ./scripts/setup.sh
```

Set `LENSES_WORKSPACE_ROOT` to your multi-repo parent if **lenses** lives inside a single product repo but you want to scan all siblings.

## Configuration

Copy `workspace-registry.example.json` to `workspace-registry.json` to override handbook/forge URLs, ignore top-level directory names, or label website repos.

## Development

- Edits to **kitchensink** or **blueprints** belong in their **standalone** repositories; bump submodules here after upstream changes.
