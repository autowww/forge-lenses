# Setup and submodules

## Standalone clone

```bash
git clone <lenses-remote-url> lenses
cd lenses
./scripts/setup.sh
```

`setup.sh` initializes nested submodules **kitchensink** and **blueprints** (read-only copies; edit those frameworks in their standalone repositories).

## As a submodule in another repo

From your product repository:

```bash
git submodule add <lenses-remote-url> lenses
git submodule update --init --recursive
```

Then run setup from inside the **lenses** submodule:

```bash
cd lenses
./scripts/setup.sh
```

## Dependencies

- **Python 3**
- **pip package `markdown`** — required only to run `generator/build-lenses-docs.py`

## Running

```bash
./scripts/run-lenses.sh
```

Optional:

```bash
export LENSES_WORKSPACE_ROOT=/path/to/workspace
./scripts/run-lenses.sh --port 8080
```

## Security

The server reads the filesystem only under the configured **workspace root** for dashboard and WBS views. Static docs are served only from **lenses-docs/** inside the **lenses** repo.
