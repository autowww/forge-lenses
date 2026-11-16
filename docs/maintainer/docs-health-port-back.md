# Docs Health — port back after Fleet / sandbox work

This note describes **operator best practice** when integrating remediation output into the real repository. It complements [docs-health-mvp.md](docs-health-mvp.md) and [git branch policy](../docs-health-git-branch-policy.md).

## Principles

1. **Never commit directly to `main`** from an automated worker. Use the **suggested branch** from the session (`feature/docs-health-…` or legacy `docs-health/…` per [git branch policy](../docs-health-git-branch-policy.md)).
2. Record **`base_sha`** (commit on trunk when the run started) on the job or in session metadata when available — merge and support use it to reproduce context.
3. **Apply** in Lenses (when enabled) writes the **host checkout** under policy; **Fleet** / Docker workers produce artifacts or patches that should be reviewed before promotion.

## Integration paths

| Path | When |
|------|------|
| **Pull request** | Preferred for Team tier: push the topic branch, open PR to `main`, require review + CI. |
| **Local merge** | `git merge --no-ff` topic into `main` after review on a trusted machine. |
| **Patch apply** | `git am` / `git apply` from exported patches when no remote push from worker is allowed. |

## Conflicts

- **Default:** human resolution (open PR, resolve in Git host UI or local three-way merge).
- **Optional automation:** only for low-risk, deterministic cases (e.g. non-overlapping hunks), behind an explicit flag; always allow **abort** and keep a backup ref.

## Durability (Fleet)

Fleet (or future remote executors) should persist **job id**, **branch name**, **base SHA**, **result SHA or artifact URI**, and **terminal status** so work can **finish while the Studio laptop is offline**; Lenses can later show **“ready to integrate”** without re-running LLM steps.

## Related

- Git policy resolver: `lenses/docs_health/git_branch_policy.py`
- Apply policy (host-only): `lenses/docs_health/isolation.py`
