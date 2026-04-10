# Lenses Studio — exploratory screenshots

Playwright-driven **tours** that open routes under `/studio/`, wait for the UI, capture PNGs, and write a **manifest** plus per-step **meta** (annotations, URL, viewport).

## Prerequisites

1. **Lenses HTTP server** reachable (default `http://127.0.0.1:8080`):

   ```bash
   cd /path/to/forge-lenses
   export PYTHONPATH="$PWD"
   export LENSES_WORKSPACE_ROOT="$PWD"   # or your multi-repo root
   python3 -m lenses --host 127.0.0.1 --port 8080
   ```

2. **Node deps** in `desktop/`:

   ```bash
   cd desktop && npm ci
   ```

3. **Linux without display:** Chromium headless is used by default; no `xvfb` required for this script.

## One-shot: full desktop + explore + pytest + E2E

From **`forge-lenses/`** repo root (starts Lenses if `/studio/` is down; retries `studio-explore` on connection errors):

```bash
./scripts/run-desktop-and-explore-checks.sh
```

## Run (default sample tour)

From **`forge-lenses/desktop/`**:

```bash
npm run studio-explore
```

Custom tour and output:

```bash
node studio-explore/runner.mjs \
  --tour studio-explore/tours/explore-default/tour.yaml \
  --out ../agents/workspaces/studio-explore/my-run
```

Environment:

| Variable | Default | Meaning |
|----------|---------|---------|
| `LENSES_BASE_URL` | `http://127.0.0.1:8080` | Origin of the Lenses server |
| `FORGE_LENSES_ROOT` | auto (`desktop/..`) | Repo root (for default `--out`) |

## Output layout

Under `agents/workspaces/studio-explore/<run-id>/` (timestamp-based by default):

```text
RUN.md
<folder-id>/
  manifest.json
  01-step-id.png
  01-step-id.meta.json
  ...
```

Each **folder** in the YAML is one subdirectory (cap **20** steps per folder by default, overridable per folder).

## Tour YAML

See [`tours/explore-default/tour.yaml`](tours/explore-default/tour.yaml). Fields:

- **`path`** — path on the Lenses server (e.g. `/studio/`, `/studio/projects`).
- **`wait_ms`** — extra delay after load (lazy routes).
- **`wait_selector`** — wait until this selector is visible.
- **`click_selector`** — click before screenshot (optional).
- **`annotation`** — human-readable note stored in `.meta.json` and `manifest.json`.

**Privacy:** screenshots may include workspace paths, project names, or PII. Do not commit `agents/workspaces/` contents unless scrubbed.
