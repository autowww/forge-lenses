# Blueprints Wizard — extending stages and artifacts

Use this checklist when adding a new **wizard step** or a new **artifact slice**. Keep changes behind the experimental flags and prefer small, typed modules.

## Add a stage (client shell)

1. **Titles** — Append a step title to `WIZARD_STEPS` in `lenses-enterprise/src/blueprints-wizard/wizardSteps.ts` and bump `WIZARD_STEP_COUNT` implicitly (length of the array).
2. **Navigation rules** — Update `applyStepNext` / `applyStepBack` in `wizardStepModel.ts` if step notes or payload keys need special handling.
3. **Shell state** — Extend `WizardShellState` / `emptyWizardShellState` in `wizardShellState.ts` if the step needs new fields; add clamp/parse helpers alongside other `*Step.ts` modules.
4. **Mapping** — Wire `wizardSessionMapping.ts` so the new fields round-trip in `payload` (and `wizard_domain` when appropriate).
5. **Validation** — Add `validateXForNext` and wire `onNext` in `BlueprintsWizardSessionPage.tsx` to block advance until valid (mirror patterns for existing steps).
6. **UI** — Add a branch in `WizardStepBody.tsx` for `stepIndex === n` (or extract a panel component under `blueprints-wizard/`).
7. **Server** — If the step needs persisted fields, extend `schemas.py` / `payload_validate.py` and document defaults in `wizard_domain_normalize.py` (Python) and `wizardDomainNormalize.ts` (TS).

## Add an artifact slice

1. **Keys** — Add the slice id to `ARTIFACT_SLICE_KEYS` in `wizard_domain_enums.py` / `wizardDomainTypes.ts` (keep lists aligned).
2. **Generation** — Extend `artifact_generation_protocol.py` / LLM prompts and `artifact_generation_llm.py` (or mock adapter) so the slice can be produced; update bundle resolution if the slice belongs to a named bundle.
3. **Normalize** — Ensure `normalizeGeneratedArtifactRecord` / `normalizeArtifactGeneration` accept the new record shape.
4. **Review / export** — `artifact_generation_service.py` (review), `artifact_export_markdown.py` (Markdown export), and `cursor_launch_pack.py` (experimental pack) may need slice-aware behavior.
5. **UI** — Review gates and artifact tables in `WizardStepBody` / review components; launch pack selection uses `ARTIFACT_SLICE_KEYS` in `ExperimentalBuildStepPanel.tsx`.

## Tests

- **pytest:** `tests/test_blueprints_wizard_*.py` for API and normalization.
- **Vitest:** Step helpers and `*.server.test.tsx` for routed flows; keep mocks in `vi.mock` of `blueprintsWizard` when the Python server is absent.

## Naming

Use `BlueprintsWizard*` or `wizard*` prefixes consistently for new files; colocate feature code under `lenses/blueprints_wizard/` (Python) and `lenses-enterprise/src/blueprints-wizard/` (TypeScript).
