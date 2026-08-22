---


nav_title: Enterprise — backup & upgrades
public_publish: true
audience: public
product_area: lenses
tier: practitioner
handbook_area: lenses
learning_level: '201'
section: enterprise
status: shipped
description: .lenses-local backup, restore, sanitization, and version rollback.
page_type: concept
---

# Enterprise — backup, retention, and upgrades

## Local data directories

| Location | Typical contents |
|----------|------------------|
| **`<workspace>/.lenses-local/`** | Wizard sessions, FTS index fragments, telemetry caches. |
| **`<workspace>/.lenses-repo/<login>/`** | GitHub overlays once PAT flows succeed. |

Scan boundaries stop at declared workspace roots — confirm **`LENSES_WORKSPACE_ROOT`** matches organizational policy before onboarding regulated repos.

## Backup and restore

| Task | Suggested approach |
|------|---------------------|
| **Backup** | Stop Lenses, archive **`<workspace>/.lenses-local/`** (tar with timestamp). Include **`.lenses-repo/`** only if GitHub overlays matter for your org. |
| **Restore** | Extract into the same workspace root while Lenses is stopped; fix ownership if copied across machines. |
| **Sanitize** | Remove `wizard-session*.json` or FTS files individually when rotating QA workspaces (faster than full wipe). |

## Upgrades and rollback

1. Record `git rev-parse HEAD` for **forge-lenses** before upgrades.
2. After `git pull`, reinstall Python deps and rebuild **`lenses-enterprise`** when the release notes say the Studio bundle changed.
3. Roll back by checking out the previous commit **and** restoring the matching **`.lenses-local/`** snapshot if new migrations were implied (rare; watch release notes).

## Audit signals (roadmap)

| Topic | Status |
|-------|--------|
| Hosted multi-tenant Wizard | **Not** a single-tenant local default — anything beyond loopback is explicit operator choice |
| Central audit SIEM export | **Planned** — rely on JSONL files today |
| Fleet-wide session replay | **Experimental** — requires Forge Fleet configuration |

## Enterprise rollout checklist

1. Confirm **`LENSES_WORKSPACE_ROOT`** aligns with git checkout policy (single vs multi-repo layouts).
2. Document bind strategy (**loopback** vs proxy) + firewall posture.
3. Decide OIDC issuer + RBAC ownership (`lenses-access.json`).
4. Decide LLM provider tier (local-first vs hosted).
5. Train admins on backup cadence before upgrades.

Cross-links: **[Configuration reference](../reference/config-env.md)**, **[Studio route atlas](14-studio-route-map.md)**.
