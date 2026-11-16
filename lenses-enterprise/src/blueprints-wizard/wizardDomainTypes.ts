/**
 * Blueprints Wizard domain enums and JSON shapes (`payload.wizard_domain`), experimental.
 * Keep in sync with `lenses/blueprints_wizard/domain_enums.py` and `wizard_domain_normalize.py`.
 */

export const MISSION_TYPES = ['explore', 'define', 'deliver', 'operate', 'sunset'] as const
export type MissionType = (typeof MISSION_TYPES)[number]

export const CONTRIBUTION_SETUP_KINDS = ['single', 'team', 'teams', 'enterprise'] as const
export type ContributionSetupKind = (typeof CONTRIBUTION_SETUP_KINDS)[number]

export const CONTEXT_SOURCES = ['repo', 'docs', 'stakeholders', 'tickets', 'metrics', 'other'] as const
export type ContextSource = (typeof CONTEXT_SOURCES)[number]

export const INTERPRETATION_FIELD_STATUSES = [
  'explicit',
  'inferred',
  'needs_confirmation',
  'unknown',
] as const
export type InterpretationFieldStatus = (typeof INTERPRETATION_FIELD_STATUSES)[number]

/** Forge methodology stages (snake_case). Legacy values map via LEGACY_TARGET_STAGE_MAP. */
export const TARGET_STAGES = [
  'idea',
  'roadmap',
  'milestones',
  'wbes',
  'ore',
  'ingots',
  'sparks',
  'charges',
] as const
export type TargetStage = (typeof TARGET_STAGES)[number]

/** Old SDLC-style stages → Forge stages (matches Python LEGACY_TARGET_STAGE). */
export const LEGACY_TARGET_STAGE_MAP: Record<string, TargetStage> = {
  discovery: 'idea',
  shape: 'roadmap',
  plan: 'milestones',
  build: 'wbes',
  verify: 'ore',
  release: 'ingots',
  operate: 'sparks',
}

export const AUTONOMY_LEVELS = [
  'l0_analyst',
  'l1_drafter',
  'l2_stage_autopilot',
  'l3_goal_autopilot',
] as const
export type AutonomyLevel = (typeof AUTONOMY_LEVELS)[number]

export const LEGACY_AUTONOMY_MAP: Record<string, AutonomyLevel> = {
  suggest_only: 'l0_analyst',
  draft_with_review: 'l1_drafter',
  execute_with_gates: 'l2_stage_autopilot',
  full_autonomy: 'l3_goal_autopilot',
}

export const MUTATION_POLICIES = [
  'read_only_analysis',
  'draft_downstream_only',
  'edit_downstream_drafts',
  'regenerate_downstream_from_approved_upstream',
  'propose_upstream_only',
] as const
export type MutationPolicy = (typeof MUTATION_POLICIES)[number]

export const LEGACY_MUTATION_MAP: Record<string, MutationPolicy> = {
  read_only: 'read_only_analysis',
  append_only: 'draft_downstream_only',
  merge_allowed: 'edit_downstream_drafts',
  replace_allowed: 'regenerate_downstream_from_approved_upstream',
}

export const OUTPUT_PACK_KINDS = [
  'foundation_pack',
  'strategy_pack',
  'planning_pack',
  'engineering_pack',
  'execution_pack',
] as const
export type OutputPackKind = (typeof OUTPUT_PACK_KINDS)[number]

export const SCOPE_BOUNDARIES = [
  'full_plan',
  'milestone',
  'wbe_subtree',
  'capability',
  'team_slice',
  'repo_path',
  'recheck_subset',
] as const
export type ScopeBoundary = (typeof SCOPE_BOUNDARIES)[number]

export const CLOSURE_OPTIONS = [
  'exact_only',
  'include_required_upstream',
  'include_shared_contracts',
  'include_downstream_impacted',
  'include_verification_artifacts',
] as const
export type ClosureOption = (typeof CLOSURE_OPTIONS)[number]

export const ARTIFACT_STATUSES = ['missing', 'draft', 'ready', 'stale', 'rejected'] as const
export type ArtifactStatus = (typeof ARTIFACT_STATUSES)[number]

export const PROMPT_INTENTS = ['clarify', 'expand', 'contract', 'recheck', 'export'] as const
export type PromptIntent = (typeof PROMPT_INTENTS)[number]

export const PROMPT_MODES = ['static', 'build_time_dynamic', 'runtime_dynamic'] as const
export type PromptMode = (typeof PROMPT_MODES)[number]

export const ASSUMPTION_LEDGER_STATUSES = [
  'open',
  'resolved',
  'accepted_system',
  'marked_unknown',
] as const
export type AssumptionLedgerStatus = (typeof ASSUMPTION_LEDGER_STATUSES)[number]

export type FoundationBriefJson = {
  markdown: string
  field_statuses: Record<string, InterpretationFieldStatus | string>
}

export type AssumptionLedgerEntryJson = {
  id: string
  text: string
  source?: ContextSource | string | null
  created_at?: string
  /** Defaults to `open` when omitted (legacy rows). */
  status?: AssumptionLedgerStatus | string
}

export type ArtifactPackItemJson = {
  id: string
  label: string
  status: ArtifactStatus | string
}

export type ArtifactPackJson = {
  id: string
  label: string
  items: ArtifactPackItemJson[]
}

export type ScopeSpecJson = {
  summary: string
  constraints_note: string
  wbs_rel?: string | null
  roadmap_rel?: string | null
  roadmap_section_id?: string | null
  scope_boundary: ScopeBoundary | string
  milestone_ref: string
  wbe_path: string
  capability_label: string
  team_label: string
  repo_paths: string[]
  recheck_issue_refs: string
  closure_options: ClosureOption[] | string[]
}

export type RunPlanStepJson = {
  id: string
  title: string
  detail: string
}

export type RunPlanJson = {
  id: string
  title: string
  steps: RunPlanStepJson[]
}

export type ReviewGateJson = {
  id: string
  title: string
  passed: boolean
  notes: string
}

export const RECHECK_PRIMARY_LABELS = [
  'missing',
  'blocked',
  'conflicting',
  'stale',
  'draft',
  'approved',
  'present',
] as const
export type RecheckPrimaryLabel = (typeof RECHECK_PRIMARY_LABELS)[number]

export type RecheckArtifactRowJson = {
  artifact_key: string
  primary_label: RecheckPrimaryLabel | string
  reasons: string[]
  review_status: string
  generation_id: string
  created_at: string
  parent_generation_id: string
}

export type RecheckBucketJson = {
  id: string
  worst_label: RecheckPrimaryLabel | string
  artifact_keys: string[]
}

export type RecheckRecommendationsJson = {
  regenerate_keys: string[]
  approve_first: string[]
  unlock_or_request_changes: string[]
  flag_for_review: string[]
}

export type RecheckReportJson = {
  schema_version: number
  computed_at: string
  artifacts: RecheckArtifactRowJson[]
  buckets: RecheckBucketJson[]
  recommendations: RecheckRecommendationsJson
}

export type RecheckSummaryJson = {
  checked_at: string
  passed: boolean
  issues: string[]
  report: RecheckReportJson
}

export type BuildPackPlanJson = {
  format: string
  paths: string[]
  notes: string
  allowed_write_globs: string[]
  guardrail_notes: string
}

export type PromptRecipeJson = {
  recipe_id: string
  intent: PromptIntent | string
  template_ref: string
  variables: Record<string, string>
  prompt_mode: PromptMode | string
  materialization_inputs: string[]
  placeholder_summary: string
}

export type PromptSnapshotJson = {
  snapshot_id: string
  recipe_id: string
  rendered: string
  content_hash: string
  created_at: string
}

export const ARTIFACT_REVIEW_STATUSES = [
  'pending',
  'approved',
  'changes_requested',
  'locked',
] as const
export type ArtifactReviewStatus = (typeof ARTIFACT_REVIEW_STATUSES)[number]

/** Actions accepted by `POST .../artifact-review` (includes unlock for sealed artifacts). */
export type ArtifactReviewApiAction =
  | 'approve'
  | 'request_changes'
  | 'lock'
  | 'unlock'
  | 'approve_bundle'

export const QUALITY_DIMENSIONS = [
  'groundedness',
  'completeness',
  'clarity',
  'consistency',
  'actionability',
  'traceability',
] as const
export type QualityDimension = (typeof QUALITY_DIMENSIONS)[number]

export type QualityDimensionScoreJson = {
  score: number
  rationale: string
}

export type QualityRubricJson = Record<QualityDimension | string, QualityDimensionScoreJson>

export type ArtifactLineageUpstreamJson = {
  artifact_key: string
  generation_id: string
  review_status: ArtifactReviewStatus | string
}

export type ArtifactLineageJson = {
  upstream: ArtifactLineageUpstreamJson[]
}

export type ArtifactProvenanceJson = {
  generation_id: string
  created_at: string
  provider: string
  model: string
  input_fingerprint: string
  parent_generation_id: string
  /** Present when schema_version >= 2 or after save. */
  lineage?: ArtifactLineageJson
}

export const ARTIFACT_SLICE_KEYS = [
  'foundation_brief_final',
  'assumptions_ledger',
  'roadmap',
  'milestone_outline',
  'milestone_charters',
  'wbe_tree',
  'dependency_map',
  'prd',
  'architecture_brief',
  'nfr_checklist',
  'adr_seeds',
  'ownership_review_matrix',
  'sparks_plan',
  'charge_plan',
  'implementation_tasklets',
  'acceptance_criteria',
  'execution_dependency_sequence',
  'qa_verification_checklist',
  'rollout_notes',
] as const
export type ArtifactSliceKey = (typeof ARTIFACT_SLICE_KEYS)[number]

/** Matches server default planning bundle. */
export const PLANNING_ARTIFACT_SLICE_KEYS = [
  'foundation_brief_final',
  'assumptions_ledger',
  'roadmap',
  'milestone_outline',
  'milestone_charters',
] as const satisfies readonly ArtifactSliceKey[]

export const ENGINEERING_ARTIFACT_SLICE_KEYS = [
  'wbe_tree',
  'dependency_map',
  'prd',
  'architecture_brief',
  'nfr_checklist',
  'adr_seeds',
  'ownership_review_matrix',
] as const satisfies readonly ArtifactSliceKey[]

/** Execution-oriented slices (Forge Sparks / Charge / tasklets / QA / rollout). */
export const EXECUTION_ARTIFACT_SLICE_KEYS = [
  'sparks_plan',
  'charge_plan',
  'implementation_tasklets',
  'acceptance_criteria',
  'execution_dependency_sequence',
  'qa_verification_checklist',
  'rollout_notes',
] as const satisfies readonly ArtifactSliceKey[]

/** Planning ∪ engineering (matches server `artifact_bundle` all/full). */
export const PLANNING_ENGINEERING_ARTIFACT_SLICE_KEYS = [
  ...PLANNING_ARTIFACT_SLICE_KEYS,
  ...ENGINEERING_ARTIFACT_SLICE_KEYS,
] as const satisfies readonly ArtifactSliceKey[]

export type ArtifactGenerationBundle =
  | 'planning'
  | 'engineering'
  | 'all'
  | 'execution'
  | 'complete'
  | 'full_stack'

/** Single source for UI headings, run-plan preview lines, and pack hints for artifact slices. */
export const ARTIFACT_SLICE_DISPLAY_LABELS: Record<ArtifactSliceKey, string> = {
  foundation_brief_final: 'Foundation Brief (final)',
  assumptions_ledger: 'Assumptions ledger',
  roadmap: 'Roadmap',
  milestone_outline: 'Milestone outline',
  milestone_charters: 'Milestone charters',
  wbe_tree: 'WBE tree',
  dependency_map: 'Dependency map',
  prd: 'PRD',
  architecture_brief: 'Architecture brief',
  nfr_checklist: 'NFR checklist',
  adr_seeds: 'ADR seeds',
  ownership_review_matrix: 'Ownership / review matrix',
  sparks_plan: 'Sparks plan',
  charge_plan: 'Charge plan',
  implementation_tasklets: 'Implementation tasklets',
  acceptance_criteria: 'Acceptance criteria',
  execution_dependency_sequence: 'Execution dependency sequence',
  qa_verification_checklist: 'QA verification checklist',
  rollout_notes: 'Rollout notes',
}

export type FoundationBriefFinalContentJson = {
  markdown: string
}

export type AssumptionsLedgerArtifactContentJson = {
  entries: AssumptionLedgerEntryJson[]
}

export type RoadmapThemeJson = {
  title: string
  description: string
  outcomes: string[]
}

export type RoadmapHorizonJson = {
  label: string
  notes: string
}

export type RoadmapArtifactContentJson = {
  summary: string
  themes: RoadmapThemeJson[]
  horizons: RoadmapHorizonJson[]
  trace_refs: string[]
}

export type MilestoneOutlineItemJson = {
  id: string
  title: string
  target: string
  dependencies: string[]
  success_criteria: string
  notes: string
}

export type MilestoneOutlineContentJson = {
  milestones: MilestoneOutlineItemJson[]
  trace_refs: string[]
}

export type MilestoneCharterItemJson = {
  id: string
  milestone_ref: string
  scope: string
  exit_criteria: string
  notes: string
}

export type MilestoneChartersContentJson = {
  charters: MilestoneCharterItemJson[]
  trace_refs: string[]
}

export type WbeNodeJson = {
  id: string
  title: string
  parent_id: string
  estimate: string
  notes: string
}

export type WbeTreeContentJson = {
  nodes: WbeNodeJson[]
  trace_refs: string[]
}

export type DependencyEdgeJson = {
  from_ref: string
  to_ref: string
  dep_type: string
  team: string
  notes: string
}

export type DependencyMapContentJson = {
  edges: DependencyEdgeJson[]
  trace_refs: string[]
}

export type PrdArtifactContentJson = {
  summary: string
  goals: string
  personas: string
  scope_in: string
  scope_out: string
  user_stories: string[]
  trace_refs: string[]
}

export type ArchitectureInterfaceJson = {
  name: string
  contract: string
}

export type ArchitectureBriefContentJson = {
  context: string
  containers: string
  components: string[]
  interfaces: ArchitectureInterfaceJson[]
  risks: string
  trace_refs: string[]
}

export type NfrChecklistRowJson = {
  category: string
  requirement: string
  measure: string
  status: string
}

export type NfrChecklistContentJson = {
  rows: NfrChecklistRowJson[]
  policy_notes: string[]
  trace_refs: string[]
}

export type AdrSeedItemJson = {
  id: string
  title: string
  context: string
  options: string
  decision_stub: string
}

export type AdrSeedsContentJson = {
  decisions: AdrSeedItemJson[]
  trace_refs: string[]
}

export type OwnershipReviewRowJson = {
  area: string
  owner: string
  reviewer: string
  raci: string
  handoff_notes: string
  policy_placeholder: string
}

export type OwnershipReviewMatrixContentJson = {
  rows: OwnershipReviewRowJson[]
  policy_notes: string[]
  trace_refs: string[]
}

export type GeneratedArtifactRecordJson = {
  content: Record<string, unknown>
  quality: QualityRubricJson
  review_status: ArtifactReviewStatus | string
  locked: boolean
  feedback: string
  provenance: ArtifactProvenanceJson
}

export type ArtifactGenerationJson = {
  schema_version: number
  artifacts: Partial<Record<ArtifactSliceKey, GeneratedArtifactRecordJson>>
}

/** `payload.wizard_domain` (schema v1). */
export type WizardDomainJson = {
  schema_version: number
  mission_type: MissionType | string
  contribution_setup_kind: ContributionSetupKind | string
  context_sources: string[]
  foundation_brief: FoundationBriefJson
  assumption_ledger: AssumptionLedgerEntryJson[]
  artifact_packs: ArtifactPackJson[]
  target_stage: TargetStage | string
  autonomy_level: AutonomyLevel | string
  mutation_policy: MutationPolicy | string
  scope_spec: ScopeSpecJson
  run_plan: RunPlanJson
  review_gates: ReviewGateJson[]
  artifact_status_by_id: Record<string, string>
  recheck_summary: RecheckSummaryJson
  build_pack_plan: BuildPackPlanJson
  prompt_recipe: PromptRecipeJson
  prompt_snapshot: PromptSnapshotJson | null
  artifact_generation: ArtifactGenerationJson
}
