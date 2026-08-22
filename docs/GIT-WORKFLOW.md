# Git workflow (Forge Team tier)

This repository uses **Forge SDLC Team** tier (5–12): protected `main`, short-lived branches, and **pull requests** with review. Methodology reference: [Git branching & commits (Forge)](https://blueprints.forgesdlc.com/sdlc--methodologies-forge-setup-branching-strategy.html) · [Blueprint source](https://github.com/autowww/blueprints/blob/main/sdlc/methodologies/forge/setup/BRANCHING-STRATEGY.md).

## Default branch

`main` — integrate via **pull requests**.

## Branch naming

- `feature/<short-topic>` — `lenses/` package, server, or docs.
- `fix/<short-topic>` — bugfixes.

### Optional Forge-native lanes

Some Forge SDLC product repositories adopt **`product/*`**, **`iter/*`**, **`spark/*`**, **`spike/*`**, **`release/*`**, and **`hotfix/*`** per the blueprint [branching charge pack](https://github.com/autowww/blueprints/blob/main/sdlc/methodologies/forge/setup/charge-plans/branching/README.md), with **`forge/charge.md`** as a daily view (never `charge/*` branches). **This repository** uses `feature/*` and `fix/*` unless the team documents a different policy under `docs/process/` or `forge/`.

## Pull requests

- Target **`main`**.
- At least **one** approval before merge.

## Commits

Use **`type(scope): imperative summary`**. Common **scopes**:

| Scope | Typical use |
|-------|-------------|
| `lenses` | Python package under `lenses/` |
| `server` | Server / CLI entry (if split from package) |
| `docs` | In-repo documentation |
| `blueprints` | Submodule pointer only (edit **autowww/blueprints** upstream) |
| `kitchensink` | Submodule pointer only (edit **autowww/forgesdlc-kitchensink** upstream; includes **forge-autodoc** at `kitchensink/forge-autodoc/`) |

This repo may embed **nested submodules** (`blueprints/`, `kitchensink/`). **Do not** use this repo to replace upstream edits—commit in the **standalone** repository, then bump the submodule pointer here in a **separate** commit.

## GitHub branch protection (maintainers)

On `autowww/forge-lenses`, for **`main`**:

1. Require a **pull request** before merging; require **at least one** approval.
2. Require **status checks** when workflows exist for PRs.
3. Block **force-push** and **deletion** on `main`.
