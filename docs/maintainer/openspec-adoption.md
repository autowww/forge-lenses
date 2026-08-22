# OpenSpec adoption — forge-lenses

forge-lenses runs **under the Epic execution profile**: Charge lists **Epics** (`M*E*`), one OpenSpec change per ready Epic, Lite observable SHALLs + scenarios. Core Forge teams elsewhere may keep Spark → Charge unchanged.

Canon: [`blueprints/sdlc/methodologies/forge/EPIC-EXECUTION-PROFILE.md`](../../blueprints/sdlc/methodologies/forge/EPIC-EXECUTION-PROFILE.md) · Blueprints setup guide: [`OPENSPEC-ADOPTION.md`](../../blueprints/sdlc/methodologies/forge/setup/OPENSPEC-ADOPTION.md)

## Telemetry (Forge program default)

Disable anonymous OpenSpec CLI telemetry on this workstation and in CI:

```bash
export OPENSPEC_TELEMETRY=0
```

Add to your shell profile or CI environment. Equivalent: `export DO_NOT_TRACK=1` or `openspec config set telemetry.enabled false`.

## Layout

| Path | Role |
|------|------|
| `openspec/config.yaml` | Default schema `forge-sdlc` + project context |
| `openspec/schemas/forge-sdlc/` | Copied from blueprints template pack |
| `openspec/changes/<slug>/` | One change per Charged Epic |
| `forge/charge.md` | **Active Epics** table (this repo) |

## Validate schema

```bash
cd forge-lenses
export OPENSPEC_TELEMETRY=0
openspec schema validate forge-sdlc
```

## Start a new Epic change

Only after the [ready Epic size gate](https://blueprints.forgesdlc.com/sdlc--methodologies-forge-epic-execution-profile.html) passes:

```bash
export OPENSPEC_TELEMETRY=0
openspec new change <epic-slug> --schema forge-sdlc
```

Fill `proposal.md` (include **WBS Epic ID**), `specs/**/spec.md` (Lite SHALLs), optional `design.md`, optional non-binding `tasks.md`. Humans approve acceptance **before** Charge; agents apply and verify against scenarios.

## Related

- WBS: [`docs/requirements/WBS.md`](../requirements/WBS.md)
- Charge: [`forge/charge.md`](../../forge/charge.md)
- Pilot change: [`openspec/changes/adopt-epic-execution-profile/`](../../openspec/changes/adopt-epic-execution-profile/)
