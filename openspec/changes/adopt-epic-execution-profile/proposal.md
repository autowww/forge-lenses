# adopt-epic-execution-profile

## WBS Epic ID

M1E3

## Why

forge-lenses is the Epic L3 OpenSpec pilot repository. Maintainers need a committed OpenSpec tree, forge-sdlc schema, and Charge aligned to **Epics** so agents can execute L3 work under observable acceptance instead of ad-hoc Spark rows.

## What Changes

- Initialize `openspec/` with the **forge-sdlc** schema pack and project context.
- Add maintainer adoption notes including `OPENSPEC_TELEMETRY=0`.
- Charge **M1E3** with this OpenSpec change — first real Epic under the profile.
- Document apply, verify, and archive steps for this change folder.

## Capabilities

### New Capabilities

- `epic-charge-profile` — Daily Charge exposes Active Epics under the Epic execution profile with traceable OpenSpec linkage.

### Modified Capabilities

- *(none)*

## Impact

- **Maintainers:** Charge and OpenSpec workflow for forge-lenses; WBS M1E3S2 (Charge optional) satisfied.
- **Assay:** Reviewable Charge row + Lite spec scenarios; no product UI or API surface change in this Epic.
- **Dependencies:** Blueprints Epic execution profile canon; OpenSpec CLI for validate/archive.
