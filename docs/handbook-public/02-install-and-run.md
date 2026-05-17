---

nav_title: Install and run
public_publish: true
audience: public
product_area: lenses
tier: overview
handbook_area: lenses
learning_level: '101'
section: get-started
status: shipped
description: Install and run — Forge Lenses handbook entry (start).
page_type: how-to
---

# Install and run

## What it is

Getting the Lenses **Python server** running so you can open the dashboard and Forge Studio in a browser.

```blueprint-diagram
key: linear
alt: Clone, venv, pip install, start server, open browser tabs for dashboard and Studio
caption: Install to first-loopback session without widening network exposure
```

## When to use it

First time you clone forge-lenses, or after updating dependencies.

## Time and verification

| | |
|-|--|
| **Time** | About **10–15 minutes** on a fast network (clone + venv + first run). |
| **Verify** | Open `http://127.0.0.1:8080/` (or your chosen port) — dashboard HTML loads; `http://127.0.0.1:8080/studio/` loads the Studio shell when enabled. |
| **Recover** | Port in use: change **`LENSES_PORT`** or stop the conflicting process. Broken dependencies: recreate the venv and `pip install -r requirements.txt` again. |

## Prerequisites

| Requirement | Notes |
|-------------|--------|
| **Git**, **Python 3**, **pip** | Use a venv below — do not rely on system Python on macOS/Linux if your distro is strict |
| Network | Needed once for `pip install` |

## Configuration reference

See [environment variables & Studio flags](../reference/config-env.md) when you tune ports, LLM gateways, Wizard/Vite toggles, or OIDC knobs (`reference-config-env.html` after `build-lenses-docs`).

## Standalone vs submodule

| Approach | Prefer when… |
|----------|----------------|
| **Standalone clone** | Lenses is a tool beside your product repos (typical) |
| **Submodule** | A parent “workspace” repo should pin the same Lenses revision for everyone |

Both paths end with a venv, `pip install -r requirements.txt`, and `./scripts/run-lenses.sh`.

## Steps

### Standalone clone

```bash
git clone https://github.com/autowww/forge-lenses.git
cd forge-lenses
./scripts/setup.sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
./scripts/run-lenses.sh
```

### Submodule

From a parent repo:

```bash
git submodule add https://github.com/autowww/forge-lenses.git forge-lenses
git submodule update --init --recursive
cd forge-lenses
./scripts/setup.sh
```

Then create a venv, `pip install -r requirements.txt`, and run `./scripts/run-lenses.sh` from **`forge-lenses/`**.

### Default URL

Open **http://127.0.0.1:8080/** (or the port shown in the terminal if yours differs).

## Health checks

| Check | Pass criteria |
|-------|----------------|
| Classic UI | `http://127.0.0.1:8080/` loads |
| API | `http://127.0.0.1:8080/api/workspace-state` returns JSON |
| Studio | `http://127.0.0.1:8080/studio/` loads after Classic works |

If Classic works but **Studio** does not, see [Studio 101](05-studio-101.md) and [Troubleshooting](12-troubleshooting.md).

## How to verify success

- The **Classic** dashboard loads in the browser.
- **http://127.0.0.1:8080/api/workspace-state** returns JSON.

## What to do next

- [Workspace setup](03-workspace-setup.md) — multi-repo root and config
- [Studio overview](04-studio-overview.md) — **`/studio/`**

If **`/studio/`** does not load correctly after the server is up, see [Studio 101](05-studio-101.md) and [Troubleshooting](12-troubleshooting.md).