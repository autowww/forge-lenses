# Docs Health — Git branch policy resolution

Lenses names the **suggested git branch** for a documentation remediation session using `lenses.docs_health.git_branch_policy.resolve_git_branch_policy(project_root, workspace_root=None)`.

## Discovery order

1. **`<project>/forge/branching.yml`**  
   Optional keys:
   - `trunk` or `default_branch` — integration branch (default `main`).
   - `docs_health_branch_style` or `docs_health_branches` — `legacy` / `docs-health` → branch pattern `docs-health/<10-char-prefix>`; `feature` / `team` / `github_flow` → `feature/docs-health-<prefix>`.
   - `lanes` / `use_forge_lanes` — if true, keeps **Team-tier** topic naming (`feature/docs-health-…`) unless overridden above.

2. **`<project>/docs/process/branching-profile.md`**  
   If the file mentions Forge lane paths (`product/`, `iter/`, `spark/`, etc.), policy stays **feature-prefixed** (short-lived topic branches; same as Team tier).

3. **Embedded blueprints** — `<project>/blueprints/sdlc/methodologies/forge/setup/BRANCHING-STRATEGY.md` exists (submodule in the consumer repo).

4. **Workspace-level blueprints** — `<workspace_root>/blueprints/.../BRANCHING-STRATEGY.md` when the framework is mounted next to scanned projects.

5. **Fallback** — [GIT-WORKFLOW.md](GIT-WORKFLOW.md): protected `main`, short-lived **`feature/*`** / **`fix/*`**, PR to `main`. Docs Health uses **`feature/docs-health-<session-prefix>`** by default.

## API fields

On `create_session`, the session payload may include:

- `suggested_git_branch` — string to create locally before Apply.
- `git_branch_policy` — `{ "source", "trunk", "style" }` for transparency (`style` is `feature_prefixed` or `legacy_docs_health`).

Port-back and merge guidance: [maintainer/docs-health-port-back.md](maintainer/docs-health-port-back.md).
