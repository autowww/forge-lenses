# Setup and submodules

## Standalone clone

```bash
git clone https://github.com/autowww/forge-lenses.git
cd forge-lenses
./scripts/setup.sh
```

`setup.sh` initializes nested submodules **kitchensink** and **blueprints** and runs **`lenses-startup.sh`**. On a standalone clone that affects **this** repo; when **forge-lenses** is a submodule, startup **elevates** to the superproject and creates `.lenses-*` on the **host** repo root (same as running `./forge-lenses/scripts/lenses-startup.sh` from the host).

## As a submodule (`forge-lenses/`)

From your product repository:

```bash
git submodule add https://github.com/autowww/forge-lenses.git forge-lenses
git submodule update --init --recursive
./forge-lenses/scripts/lenses-startup.sh
```

Then:

```bash
cd forge-lenses && ./scripts/setup.sh
```

## Host repo folders (parent of `forge-lenses/`)

After **`lenses-startup.sh`** (from the host tree or from inside `forge-lenses/`; submodule checkouts are redirected to the superproject):

- **`.lenses-local/`** — gitignored; local-only (sessions cache, **`sticker-board.json`** marker or full local board, **`sticker-board-shared-local.json`** overlay when using a shared board, etc.).
- **`.lenses-repo/<github-login>/`** — committed (starts with `.gitkeep`; optional `README.txt` added only if missing). This is the commit-friendly “shared with the repo” area (some people think of it as a lenses-shared slot; the directory name is **`.lenses-repo/`**). GitHub login from **`gh api user`**, else **`git remote get-url origin`** on the **resolved git repo** (`github.com/owner/...`).

### Multi-repo workspace parent (sibling repos)

If **forge-lenses** is a checkout next to other repos (not a submodule of a meta-repo), set **`LENSES_WORKSPACE_ROOT`** to that parent directory so **`.lenses-local/`** and **`.lenses-repo/`** are created there (same variable the server uses for scanning). Example:

```bash
export LENSES_WORKSPACE_ROOT=/path/to/workspace
cd /path/to/workspace/forge-lenses && ./scripts/setup.sh
```

## Dependencies

- **Python 3**
- **`markdown`** (pip) — for `generator/build-lenses-docs.py` only

## Running

```bash
cd forge-lenses
./scripts/run-lenses.sh
```

Optional:

```bash
export LENSES_WORKSPACE_ROOT=/path/to/workspace
./scripts/run-lenses.sh --port 8080
```

## Security

The server reads the workspace only under the configured **workspace root**. Static docs are served only from **lenses-docs/** inside **forge-lenses**.
