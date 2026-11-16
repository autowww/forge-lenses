# Sprint 1 walkthrough: canonical orchestration graph

This walkthrough validates **one story traced end-to-end** using the bundled demo seed (`ogs:demo:story:rate-limit-auth`).

## Prerequisites

- Run Lenses: `python3 -m lenses` from a workspace root (or open Forge Studio / Electron against the same server).
- Default: **`LENSES_EXPERIMENTAL_ORCHESTRATION_GRAPH`** unset (enabled) and **`LENSES_ORCHESTRATION_AUTO_SEED`** unset (auto-load demo when the orchestration DB is empty).

## Steps

1. **Confirm graph is loaded**  
   Open `GET http://127.0.0.1:8080/api/orchestration/status` — expect `ok: true`, `entity_count: 17`, `edge_count: 19`.

2. **Fetch a trace**  
   Open  
   `GET http://127.0.0.1:8080/api/orchestration/trace?root=ogs:demo:story:rate-limit-auth&direction=both&max_depth=8&max_nodes=500`  
   In the JSON, confirm nodes include kinds: **objective → initiative → epic → story → task**, **change_request**, **commit**, **branch**, **repo**, **build**, **test_run**, **artifact**, **release**, **environment**, **vulnerability**, **incident**, **evidence**.

3. **Verify typed edges (spot checks)**  
   In `edges`, find:
   - `implements`: PR → story  
   - `documented_by`: story → evidence  
   - `tests`: build / test_run → story  
   - `deploys`: release → environment  
   - `affects`: vulnerability → release  
   - `caused_by`: incident → vulnerability  
   - `mitigates`: release → vulnerability  

4. **Studio drawer**  
   - **Workspace**: Home → **Trace sample story**.  
   - **Plans**: Plan summary tab → **Trace sample story (demo graph)**.  
   - **Delivery**: Plan → Today → **Trace (demo)** in the action band, or **Open trace graph** on the pipeline card.  
   - **Projects**: Open any project dashboard → **Trace sample story** (and **Trace repo (demo)** when the child name matches the seeded repo slug, e.g. `forgesdlc` → `ogs:demo:repo:forgesdlc`).

5. **Reload seed (optional)**  
   From loopback: `curl -X POST http://127.0.0.1:8080/api/orchestration/seed-demo`  
   Re-applies the demo fixture (useful after manual DB edits).

## Static museum

With `VITE_STATIC_MUSEUM=true`, trace calls resolve to **`museum-data/orchestration-trace.json`** so the drawer still renders a fixed subgraph without SQLite.

## Clearing local state

Delete **`<workspace>/.lenses-local/lenses-orchestration.sqlite`** and restart the server to get a fresh auto-seeded demo DB.
