# Reader journeys — gap-bridge closure checklist

Run these evaluator→builder paths before declaring handbook parity acceptable for a Forge Lenses release candidate.
Capture the validating git SHA beside each row when executing locally (`git rev-parse HEAD`).

## 1. Auditor lands on the public handbook shell

1. Build with `bash scripts/check-docs.sh` or at least `python3 generator/build-lenses-docs.py` (public profile).
2. Open **`lenses-docs/index.html`** in a browser — confirm nav renders and the handbook introduction reads coherently.
3. Drill into **`lenses-docs/builders-schemas.html`** from the Builders section and confirm the schema bundle table mentions `wizard-session.schema.json`.

**Last verified SHA:** _

## 2. Operator reproduces workspace setup + scan evidence

1. Read **`docs/handbook-public/03-workspace-setup.md`** and the **`03-workspace-setup_03-scan-host.md`** appendix.
2. Read **`docs/handbook-public/builders-openapi.md`** and **`docs/handbook-public/16-schemas-and-api-for-builders.md`** — confirm **`/api/repo`** appears in the handbook corpus beside workspace scan guidance (`/api/workspace-scan`, `/api/workspace-state`).
3. Optionally run **`curl http://127.0.0.1:8080/api/workspace-scan`** per local install instructions (swap host/port).

**Last verified SHA:** _

## 3. Auditor validates Docs Health API surfaces + scenario narrative

1. Read **`docs/handbook-public/15-docs-health.md`** and **`examples-scenario-docs-health.md`**.
2. Cross-check **`/api/docs-health/summary`** and **`/api/docs-health/work-items`** against `lenses/website/http-api-and-routes.md` (exported as **`lenses-docs/generated-api-routes.html`**).
3. Run **`pytest tests/test_docs_schemas.py`** — ensures `docs-health-work-item.schema.json` stays paired.

**Last verified SHA:** _

## 4. Security engineer validates auth + Fleet boundaries

1. Read **`docs/handbook-public/builders-auth-and-safety.md`** and **`docs/handbook-public/13-llm-and-ai-setup.md`**.
2. Probe **`curl http://127.0.0.1:8080/api/auth/status`** on a reachable instance.
3. Scan the **`/api/fleet`** route rows in **`lenses-docs/generated-api-routes.html`** and confirm handbook prose cites Forge Fleet bridging.

**Last verified SHA:** _

## 5. Wizard facilitator walks the 101→301 ladder + scenario hub

1. Read **`docs/handbook-public/09-wizard-101.md`**, **`10-wizard-201.md`**, and **`11-wizard-301.md`** (linked children as needed).
2. Open **`docs/handbook-public/26-examples-scenarios-hub.md`** in the editor (or **`lenses-docs/26-examples-scenarios-hub.html`** after build) and spot-check two linked scenario dossiers (`examples-scenario-*.md`).

**Last verified SHA:** _

## 6. Release manager exercises deploy parity + generated artefacts

1. Read **`docs/handbook-public/builders-openapi.md`** and open **`docs/generated/openapi.json`** (or **`lenses-docs/generated-api-routes.html`**) after a doc build.
2. Run **`bash scripts/check-docs.sh`** locally before tagging.
3. When outbound network access is acceptable, optionally run **`python3 scripts/check-live-docs-parity.py --allow-network`** after publishing; paste the summarized output into your release Ember log entry.

**Last verified SHA:** _

## Maintainer note

Leaving **Last verified SHA** blank is acceptable only during draft branches; handbook release tags should record real SHAs. Offline operators may defer live parity (**journey 6, step 3**) but must schedule it within seven days.
