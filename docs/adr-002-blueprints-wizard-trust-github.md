# ADR 002: Blueprints Wizard — trust boundary and GitHub repository creation

## Status

Accepted (experimental feature; server-gated).

## Context

The Blueprints Wizard in Lenses Studio persists **draft** methodology work under `.lenses-local/blueprints-wizard/sessions/`. A planned capability is **creating a new GitHub repository** from wizard metadata (visibility, name, owner). That crosses a trust boundary: **network egress**, **OAuth/PAT handling**, and **non-local side effects**.

## Decision

1. **Session-first drafts:** All wizard fields (including intended repo metadata) live in **session JSON** until the user runs an explicit **Create repository** action. No automatic remote mutations on autosave or step navigation.

2. **Privileged operations:** Endpoints that call the **GitHub REST API** or **LLM** require the same **loopback-only** (or `LENSES_ALLOW_ACTIONS`) policy already used by `/api/llm/chat` and related routes. Remote clients must not invoke these without an explicit future design.

3. **Token storage:** The server reads **`GITHUB_TOKEN`** or **`LENSES_GITHUB_TOKEN`** from the **environment** (or process manager). **Do not** persist personal access tokens in session JSON or unencrypted `.lenses-local` files. Future work may add OS keychain or a GitHub App; document in a follow-up ADR.

4. **Runtime location:** GitHub calls run **inside the Lenses Python process** (`lenses/blueprints_wizard/`), wired through thin handlers in `lenses/serve.py` — **no** separate microservice for v1. If quotas or isolation require it, replace the implementation behind the same HTTP contract.

5. **Scope binding (WBS / Roadmap):** Paths stored in session payload (`wbs_rel`, `roadmap_rel`) are validated with the same **workspace path-safety** rules as existing roadmap/WBS APIs (under workspace root, expected path segments, file must exist).

## Consequences

- Operators must **export a token** in the server environment when using Create repository; missing token yields a clear JSON error.
- Submodule or local git operations remain **out of scope** unless covered by a separate ADR and explicit UI.

## Related documentation

- [docs/blueprints/wizard-implementation-plan.md](blueprints/wizard-implementation-plan.md)
- [.cursor/rules/blueprints-wizard-experimental.mdc](../.cursor/rules/blueprints-wizard-experimental.mdc)
