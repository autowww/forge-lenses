# Blueprints Wizard — domain model (`wizard_domain`)

Experimental feature. Server and Studio default **on**; opt out with env (see `docs/blueprints/wizard-file-map.md`).

## Location

Structured wizard data lives under **`session.payload.wizard_domain`** in the session JSON file (`.lenses-local/blueprints-wizard/sessions/<id>.json`). The object has **`schema_version: 1`** and is merged on every load via normalization (Python: `lenses/blueprints_wizard/wizard_domain_normalize.py`; Studio: `wizardDomainNormalize.ts`).

Legacy sibling keys remain on **`payload`** for existing flows: **`mission`**, **`contributionSetup`**, **`contextIntake`**, **`scope`** (path validation), **`foundation_brief`** (LLM refine output), **`stepNotes`**, **`targetOutputPack`**, **`autonomyMutation`**, **`scopeSelection`**, etc. The enum **`contribution_setup_kind`** in `wizard_domain` describes scale (**single / team / teams / enterprise**); it does **not** replace the free-text **`contributionSetup`** step object.

## Enums

| Name | Values |
|------|--------|
| MissionType | `explore`, `define`, `deliver`, `operate`, `sunset` |
| ContributionSetupKind | `single`, `team`, `teams`, `enterprise` |
| ContextSource | `repo`, `docs`, `stakeholders`, `tickets`, `metrics`, `other` |
| InterpretationFieldStatus | `explicit`, `inferred`, `needs_confirmation`, `unknown` |
| TargetStage | `idea`, `roadmap`, `milestones`, `wbes`, `ore`, `ingots`, `sparks`, `charges` (Forge methodology stages) |
| OutputPackKind (payload `targetOutputPack`) | `foundation_pack`, `strategy_pack`, `planning_pack`, `engineering_pack`, `execution_pack` |
| AutonomyLevel | `l0_analyst`, `l1_drafter`, `l2_stage_autopilot`, `l3_goal_autopilot` |
| MutationPolicy | `read_only_analysis`, `draft_downstream_only`, `edit_downstream_drafts`, `regenerate_downstream_from_approved_upstream`, `propose_upstream_only` |
| ScopeBoundary (`scope_spec`) | `full_plan`, `milestone`, `wbe_subtree`, `capability`, `team_slice`, `repo_path`, `recheck_subset` |
| ClosureOption (`scope_spec.closure_options`) | `exact_only`, `include_required_upstream`, `include_shared_contracts`, `include_downstream_impacted`, `include_verification_artifacts` |
| ArtifactStatus | `missing`, `draft`, `ready`, `stale`, `rejected` |
| PromptIntent | `clarify`, `expand`, `contract`, `recheck`, `export` |
| PromptMode (`prompt_recipe.prompt_mode`) | `static`, `build_time_dynamic`, `runtime_dynamic` |

Invalid or missing enum strings are coerced to documented defaults during normalization.

**Legacy mapping (load-only):** older sessions may contain SDLC-style target stages (`discovery` … `operate`), legacy autonomy (`suggest_only` …), or legacy mutation (`read_only` …). These are mapped to the Forge tokens above on normalize (see `domain_enums.py`). **`propose_upstream_only`** means upstream changes are proposals only; the wizard never silently applies upstream edits—persisted policies inform prompts and downstream automation must respect them.

## Composite shapes (summary)

| Key | Role |
|-----|------|
| `foundation_brief` | `{ markdown, field_statuses }` — `field_statuses` maps field keys to InterpretationFieldStatus |
| `assumption_ledger` | List of `{ id, text, source?, created_at? }` |
| `artifact_packs` | List of `{ id, label, items[] }` with items `{ id, label, status }` |
| `scope_spec` | `{ summary, constraints_note, wbs_rel?, roadmap_rel?, roadmap_section_id?, scope_boundary, milestone_ref, wbe_path, capability_label, team_label, repo_paths[], recheck_issue_refs, closure_options[] }` — narrative, boundary metadata, optional path mirrors; **`payload.scope`** remains authoritative for `payload_validate` path checks |
| `run_plan` | `{ id, title, steps[] }` with steps `{ id, title, detail }` |
| `review_gates` | List of `{ id, title, passed, notes }` |
| `artifact_status_by_id` | Map of artifact id → ArtifactStatus |
| `recheck_summary` | `{ checked_at, passed, issues[], report }` — **`report`** is schema **v1** (see below) |
| `build_pack_plan` | `{ format, paths[], notes, allowed_write_globs[], guardrail_notes }` |
| `prompt_recipe` | `{ recipe_id, intent, template_ref, variables{}, prompt_mode, materialization_inputs[], placeholder_summary }` — `prompt_mode`: `static` \| `build_time_dynamic` \| `runtime_dynamic` |
| `prompt_snapshot` | Nullable `{ snapshot_id, recipe_id, rendered, content_hash, created_at }` |

`artifact_generation.artifacts` holds generated slices keyed by stable names. Besides planning and engineering slices (foundation brief final through ownership matrix), **execution** slices include: `sparks_plan`, `charge_plan`, `implementation_tasklets` (each tasklet lists `upstream_artifacts` with `artifact_key` for traceability), `acceptance_criteria`, `execution_dependency_sequence`, `qa_verification_checklist`, `rollout_notes`. Bundle names `all` / `full` select planning+engineering only; `execution` selects execution slices; `complete` / `full_stack` selects every slice.

Unknown keys at the **top level** of `wizard_domain` are preserved across normalization for forward compatibility.

### `recheck_summary.report` (schema v1)

Populated by `POST /api/blueprints/wizard/session/<id>/artifact-recheck` (deterministic engine; no extra LLM). Fields:

| Field | Meaning |
|-------|--------|
| `schema_version` | Always `1` for this shape |
| `computed_at` | UTC timestamp when the report was computed |
| `artifacts[]` | One row per known artifact slice key: `artifact_key`, `primary_label` (`missing` \| `blocked` \| `conflicting` \| `stale` \| `draft` \| `approved` \| `present`), `reasons[]`, `review_status`, `generation_id`, `created_at`, `parent_generation_id` |
| `buckets[]` | Aggregates by methodology bucket: `id` (`planning` \| `engineering` \| `execution`), `worst_label`, `artifact_keys[]` |
| `recommendations` | `regenerate_keys`, `approve_first`, `unlock_or_request_changes`, `flag_for_review` (string hints for scope / human review) |

## Session state (Python)

Pure helpers live in `lenses/blueprints_wizard/wizard_session_state.py`: selectors (`get_wizard_domain`, `get_run_plan`, …) and immutable updates (`merge_wizard_domain`, `append_assumption_entry`, `set_step_index`, …). Optional **`RecheckProvider`** / **`NullRecheckProvider`** are in `recheck_provider.py` for future recheck passes without a heavy implementation today.

## Studio UI (Lenses Enterprise)

Mission **type** and contribution **scale** are edited on steps 0–1 (`WizardStepBody`) and persisted under `payload.wizard_domain` via `mergeShellIntoWizardDocument`. The refine panel shows **read-only** brief Markdown (domain + legacy), supports **editing** `assumption_ledger` rows (add/remove/text/source) and **foundation_brief.field_statuses** (per-field interpretation confidence), each persisted with **`PUT`** session. Successful **refine** sets `field_statuses.llm_foundation_brief` to `inferred` and writes Markdown to both legacy `payload.foundation_brief` and `wizard_domain.foundation_brief.markdown` (see `refine.py`).

## Persistence

Server: existing session store + `PUT /api/blueprints/wizard/session/<id>`. Local Studio (API off): `wizardPersistence.ts` uses storage key **`lenses.studio.blueprintsWizard.shell.v2`** and may include optional **`wizardDomain`** alongside shell fields.
