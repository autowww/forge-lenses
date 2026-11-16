# Workcells orchestration (post-MVP)

**Status:** Design only — not implemented in the Micro Agent MVP.

## Intent

**Forge Lenses** remains the control plane for ForgeRun visibility and human review. Runnable workcells live in the private **forge-workcells** repo (`autowww/forge-workcells`), not in **forge-platform**.

## Planned integration

1. Add git submodule `forge-workcells/` (SSH, org read access).
2. API surface to invoke `local_llm_worker` (and later workcells) with `WorkcellRequest` / `WorkcellResult` envelopes aligned to platform schemas.
3. Project UI: link `arun_*` artifacts under `.forge/runs/` or workbench out dirs to Lenses evidence panels.

## Out of scope until harness green

- Replacing KS `invoke-ai-ruleset-harness.sh` from Lenses UI
- Submoduling **forge-platform** into Lenses (forbidden — consume handbook URLs and schemas only)

## Reference

- [Forge Platform ecosystem reference](https://github.com/autowww/forge-platform/blob/main/docs/ecosystem-reference.md)
- [ADR-0008 platform sibling / workcells](https://github.com/autowww/forge-platform/blob/main/adr/ADR-0008-platform-sibling-workcells.md)
