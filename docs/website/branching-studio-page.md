# Lenses Studio — project Branching page

**Audience:** operators and engineers extending **Forge Lenses Studio**, or explaining **Branch Steward** policy to a delivery team.

**Product surface:** Lenses Studio React app — **`/studio/projects/<project>/branching`**. Data comes from **`GET /api/project/<project>/branching`** (same origin as the dashboard).

Classic Lenses still exposes **Repo & strategy** at **`/projects/<name>/strategy`** (submodules, registry text, optional `LENSES-REPO-STRATEGY.md`). Studio **Branching** focuses on **resolved policy**, **merge guardrails**, **prefix conventions**, **live scan hints**, and optional **fixture-backed** branch/PR/protection rows — see [Dashboard pages](dashboard-pages.md) for Classic narrative.

## HTTP payload (`schema_version` 1)

Successful responses include:

| Field | Role |
|-------|------|
| **`ok`** | Boolean success flag. |
| **`schema_version`** | Integer; currently **1**. |
| **`project`** | Workspace child name (directory slug). |
| **`policy`** | Resolved Branch Steward policy: source path, trunk, model (`team_tier` or `forge_lanes`), team scale/topology/CI maturity gloss inputs, prefix map, merge guardrails, Docs Health branch style. |
| **`current`** | Local git scan hints: current branch, short `HEAD`, `origin` URL, whether git metadata was present. |
| **`structure`** | Normalized **branches**, **branches_by_lane**, **pull_requests**, **branch_protection**, optional **work_item_links** — populated when repo-workflow fixtures or provider snapshots are merged (see below). |
| **`recommendations`** | Short operator/agent strings keyed by intent (`charge_work`, `ad_hoc_user_task`, …). |
| **`hints`** | Workspace-level strings (for example missing `.lenses-local/repo-workflow.json`). |

Authoritative construction: Python **`lenses/project_branching.py`** (`build_project_branching_payload`).

## Policy resolution order

Branch Steward reads the repository root in this order (first match wins):

1. **`forge/branching.yml`** — explicit lanes, promotion rules, prefixes.
2. **`docs/process/branching-profile.md`** — when text suggests Forge lanes, model may resolve to **forge_lanes** (heuristic).
3. **`forge/forge.config.yaml`** — `team.scale` and related fields map to a **team_tier** profile (see **`lenses/branch_steward_policy.py`**, `_from_forge_config`).
4. **`blueprints/sdlc/methodologies/forge/setup/BRANCHING-STRATEGY.md`** inside the repo — defaults to team-tier assumptions with methodology citation as the policy source.
5. Same blueprints path on the **workspace root** (meta-repo with shared blueprints).
6. **Fallback** — conservative team-tier defaults when nothing else matches.

## `structure` and repo workflow

Lane grouping and PR tables require normalized **repo workflow** data. The server merges workspace scan with **`.lenses-local/repo-workflow.json`** per child, or the demo seed when **`LENSES_REPO_WORKFLOW_SEED_DEMO=1`**. When no fixture exists, **`structure.branches`** may be empty and hints explain how to enable richer widgets — see **`lenses/repo_workflow/aggregate.py`**.

Feature flag: **`LENSES_EXPERIMENTAL_REPO_WORKFLOW`** (off forces minimal structure).

## Studio UI mapping

Human-readable sections on the Branching page map to payload blocks as follows:

1. **Governed integration model** — `policy` (source, model, trunk, team profile sentence, Docs Health style).
2. **Merge and quality gates** — `require_pr`, `required_approvals`, `require_green_checks` rendered as prose (host rules may differ).
3. **Policy resolution order** — ordered ladder with the resolved `policy.source` highlighted.
4. **Payload map** — card grid for top-level JSON blocks with anchor to raw JSON.
5. **Branching topology** — model-specific SVG plus optional Kitchensink roadmap thumbnail (`/__ks/…`).
6. **Branch naming conventions** — table of `policy.*_prefix` rows; not a live remote branch list.
7. **Live repository signals** — `current`, `hints`, lane bar chart, category mix, PR map and tables when data exists.
8. **Operator and agent playbook** — `recommendations` with human titles (keys remain stable for automation).
9. **Technical details** — full JSON for integrators.

View-model helpers live in **`lenses-enterprise/src/lib/branchingViewModel.ts`** (formatters only; no API contract change). Interactive charts and topology figures live in **`lenses-enterprise/src/components/projects/BranchingVisuals.tsx`**.

## Reference figures (handbook)

Static SVG sketches mirror the Studio page. They are documentation-only (not a second source of truth for policy).

<figure>
<figcaption style="font-size:0.9rem;margin-bottom:0.35rem"><strong>Figure 1 — Policy resolution ladder (first match wins)</strong></figcaption>
<svg xmlns="http://www.w3.org/2000/svg" width="440" height="200" viewBox="0 0 440 200" role="img" aria-label="Six ordered steps from forge branching yaml to fallback">
  <rect x="8" y="8" width="200" height="22" rx="4" fill="#e7f1ff" stroke="#0d6efd"/>
  <text x="16" y="23" font-size="11" fill="#052c65">1 forge/branching.yml</text>
  <rect x="8" y="38" width="240" height="22" rx="4" fill="#f8f9fa" stroke="#adb5bd"/>
  <text x="16" y="53" font-size="11" fill="#495057">2 docs/process/branching-profile.md (heuristic)</text>
  <rect x="8" y="68" width="200" height="22" rx="4" fill="#f8f9fa" stroke="#adb5bd"/>
  <text x="16" y="83" font-size="11" fill="#495057">3 forge/forge.config.yaml</text>
  <rect x="8" y="98" width="260" height="22" rx="4" fill="#f8f9fa" stroke="#adb5bd"/>
  <text x="16" y="113" font-size="11" fill="#495057">4 blueprints/…/BRANCHING-STRATEGY.md</text>
  <rect x="8" y="128" width="280" height="22" rx="4" fill="#f8f9fa" stroke="#adb5bd"/>
  <text x="16" y="143" font-size="11" fill="#495057">5 workspace/blueprints/…/BRANCHING-STRATEGY.md</text>
  <rect x="8" y="158" width="160" height="22" rx="4" fill="#fff3cd" stroke="#ffc107"/>
  <text x="16" y="173" font-size="11" fill="#664d03">6 Built-in fallback</text>
</svg>
</figure>

<figure>
<figcaption style="font-size:0.9rem;margin-bottom:0.35rem"><strong>Figure 2 — Branching API payload blocks (v1)</strong></figcaption>
<svg xmlns="http://www.w3.org/2000/svg" width="440" height="120" viewBox="0 0 440 120" role="img" aria-label="Five payload blocks policy current structure recommendations hints around project">
  <rect x="10" y="40" width="88" height="48" rx="6" fill="#d1e7dd" stroke="#198754"/>
  <text x="54" y="68" text-anchor="middle" font-size="11" fill="#0a3622">project</text>
  <rect x="110" y="10" width="72" height="36" rx="6" fill="#e7f1ff" stroke="#0d6efd"/>
  <text x="146" y="32" text-anchor="middle" font-size="10" fill="#052c65">policy</text>
  <rect x="200" y="10" width="72" height="36" rx="6" fill="#e7f1ff" stroke="#0d6efd"/>
  <text x="236" y="32" text-anchor="middle" font-size="10" fill="#052c65">current</text>
  <rect x="290" y="10" width="72" height="36" rx="6" fill="#e7f1ff" stroke="#0d6efd"/>
  <text x="326" y="32" text-anchor="middle" font-size="10" fill="#052c65">structure</text>
  <rect x="140" y="70" width="100" height="36" rx="6" fill="#f8f9fa" stroke="#6c757d"/>
  <text x="190" y="92" text-anchor="middle" font-size="10" fill="#495057">recommendations</text>
  <rect x="260" y="70" width="72" height="36" rx="6" fill="#f8f9fa" stroke="#6c757d"/>
  <text x="296" y="92" text-anchor="middle" font-size="10" fill="#495057">hints</text>
</svg>
</figure>

## See also

- [HTTP API and routes](../lenses/website/http-api-and-routes.md) — **`GET /api/project/<name>/branching`** row in the JSON API table.
- [Interface pages](interface-pages.md) — dual-surface architecture (Classic vs Studio).
- [Branching strategy (Blueprints)](https://github.com/autowww/blueprints/blob/main/sdlc/methodologies/forge/setup/BRANCHING-STRATEGY.md) — methodology source for defaults.
