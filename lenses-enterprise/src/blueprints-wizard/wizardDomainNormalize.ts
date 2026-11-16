/**
 * Normalize `payload.wizard_domain` — mirror `lenses/blueprints_wizard/wizard_domain_normalize.py`.
 */

import type {
  WizardDomainJson,
  FoundationBriefJson,
  AssumptionLedgerEntryJson,
  ArtifactPackJson,
  ScopeSpecJson,
  RunPlanJson,
  ReviewGateJson,
  RecheckSummaryJson,
  RecheckReportJson,
  RecheckArtifactRowJson,
  RecheckBucketJson,
  RecheckRecommendationsJson,
  BuildPackPlanJson,
  PromptRecipeJson,
  PromptSnapshotJson,
  ArtifactGenerationJson,
  GeneratedArtifactRecordJson,
  QualityRubricJson,
  QualityDimensionScoreJson,
  ArtifactLineageJson,
  ArtifactLineageUpstreamJson,
} from './wizardDomainTypes'
import {
  ARTIFACT_SLICE_KEYS,
  ARTIFACT_REVIEW_STATUSES,
  QUALITY_DIMENSIONS,
  RECHECK_PRIMARY_LABELS,
} from './wizardDomainTypes'
import {
  ARTIFACT_STATUSES,
  ASSUMPTION_LEDGER_STATUSES,
  AUTONOMY_LEVELS,
  CLOSURE_OPTIONS,
  CONTEXT_SOURCES,
  CONTRIBUTION_SETUP_KINDS,
  INTERPRETATION_FIELD_STATUSES,
  LEGACY_AUTONOMY_MAP,
  LEGACY_MUTATION_MAP,
  LEGACY_TARGET_STAGE_MAP,
  MISSION_TYPES,
  MUTATION_POLICIES,
  PROMPT_INTENTS,
  PROMPT_MODES,
  SCOPE_BOUNDARIES,
  TARGET_STAGES,
  type AutonomyLevel,
  type ClosureOption,
  type MutationPolicy,
  type ScopeBoundary,
  type TargetStage,
} from './wizardDomainTypes'

function coerceStr(v: unknown): string {
  if (v === null || v === undefined) return ''
  return String(v).trim()
}

function coerceOptStr(v: unknown): string | null {
  if (v === null || v === undefined) return null
  const s = String(v).trim()
  return s || null
}

function normKey(raw: unknown): string {
  return coerceStr(raw).toLowerCase().replace(/\s+/g, '_').replace(/-/g, '_')
}

function coerceEnum<T extends string>(raw: unknown, allowed: readonly T[], fallback: T): T {
  const s = normKey(raw)
  if (!s) return fallback
  return (allowed as readonly string[]).includes(s) ? (s as T) : fallback
}

function coerceTargetStage(raw: unknown): TargetStage {
  const s = normKey(raw)
  if (!s) return 'idea'
  const mapped = (LEGACY_TARGET_STAGE_MAP as Record<string, string>)[s] ?? s
  return (TARGET_STAGES as readonly string[]).includes(mapped) ? (mapped as TargetStage) : 'idea'
}

function coerceAutonomyLevel(raw: unknown): AutonomyLevel {
  const s = normKey(raw)
  if (!s) return 'l0_analyst'
  const mapped = (LEGACY_AUTONOMY_MAP as Record<string, string>)[s] ?? s
  return (AUTONOMY_LEVELS as readonly string[]).includes(mapped) ? (mapped as AutonomyLevel) : 'l0_analyst'
}

function coerceMutationPolicy(raw: unknown): MutationPolicy {
  const s = normKey(raw)
  if (!s) return 'read_only_analysis'
  const mapped = (LEGACY_MUTATION_MAP as Record<string, string>)[s] ?? s
  return (MUTATION_POLICIES as readonly string[]).includes(mapped) ? (mapped as MutationPolicy) : 'read_only_analysis'
}

function coerceScopeBoundary(raw: unknown): ScopeBoundary {
  return coerceEnum(raw, SCOPE_BOUNDARIES, 'full_plan')
}

export function normalizeClosureOptionsList(raw: unknown): ClosureOption[] {
  if (!Array.isArray(raw)) return []
  const seen = new Set<string>()
  const out: ClosureOption[] = []
  for (const x of raw) {
    const s = normKey(x)
    if (!s || !(CLOSURE_OPTIONS as readonly string[]).includes(s) || seen.has(s)) continue
    seen.add(s)
    out.push(s as ClosureOption)
  }
  return [...out].sort()
}

function newEntryId(): string {
  const a = new Uint8Array(12)
  crypto.getRandomValues(a)
  return Array.from(a, (b) => b.toString(16).padStart(2, '0')).join('')
}

function coerceSchemaVersion(raw: unknown): number {
  if (typeof raw === 'number' && Number.isFinite(raw)) return Math.max(1, Math.floor(raw))
  if (typeof raw === 'string' && /^\d+$/.test(raw)) return Math.max(1, parseInt(raw, 10))
  return 1
}

export function normalizeFoundationBrief(raw: unknown): FoundationBriefJson {
  const defaults: FoundationBriefJson = { markdown: '', field_statuses: {} }
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return { ...defaults }
  const o = raw as Record<string, unknown>
  const out: FoundationBriefJson = {
    markdown: coerceStr(o.markdown).slice(0, 120_000),
    field_statuses: {},
  }
  const fs = o.field_statuses
  if (fs && typeof fs === 'object' && !Array.isArray(fs)) {
    for (const [k, val] of Object.entries(fs as Record<string, unknown>)) {
      const key = coerceStr(k).slice(0, 200)
      if (!key) continue
      out.field_statuses[key] = coerceEnum(val, INTERPRETATION_FIELD_STATUSES, 'unknown')
    }
  }
  return out
}

export function normalizeAssumptionLedgerEntry(raw: unknown): AssumptionLedgerEntryJson | null {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null
  const o = raw as Record<string, unknown>
  let id = coerceStr(o.id).slice(0, 128)
  if (!id) id = newEntryId()
  const text = coerceStr(o.text).slice(0, 16_000)
  let source: string | null | undefined
  if (o.source === null || o.source === undefined || (typeof o.source === 'string' && !o.source.trim())) {
    source = undefined
  } else {
    source = coerceEnum(o.source, CONTEXT_SOURCES, 'other')
  }
  const created_at =
    o.created_at !== null && o.created_at !== undefined ? coerceStr(o.created_at).slice(0, 64) : ''
  const status = coerceEnum(o.status, ASSUMPTION_LEDGER_STATUSES, 'open')
  return { id, text, source: source ?? undefined, created_at, status }
}

export function normalizeAssumptionLedger(raw: unknown): AssumptionLedgerEntryJson[] {
  if (!Array.isArray(raw)) return []
  const out: AssumptionLedgerEntryJson[] = []
  for (const item of raw) {
    const n = normalizeAssumptionLedgerEntry(item)
    if (n) out.push(n)
  }
  return out
}

export function normalizeArtifactPackItem(raw: unknown): { id: string; label: string; status: string } | null {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null
  const o = raw as Record<string, unknown>
  const id = coerceStr(o.id).slice(0, 128) || newEntryId()
  const label = coerceStr(o.label).slice(0, 500)
  const status = coerceEnum(o.status, ARTIFACT_STATUSES, 'missing')
  return { id, label, status }
}

export function normalizeArtifactPack(raw: unknown): ArtifactPackJson {
  const defaults: ArtifactPackJson = { id: '', label: '', items: [] }
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return { ...defaults }
  const o = raw as Record<string, unknown>
  const id = coerceStr(o.id).slice(0, 128) || newEntryId()
  const label = coerceStr(o.label).slice(0, 500)
  const items: ArtifactPackJson['items'] = []
  if (Array.isArray(o.items)) {
    for (const it of o.items) {
      const n = normalizeArtifactPackItem(it)
      if (n) items.push(n)
    }
  }
  return { id, label, items }
}

export function normalizeScopeSpec(raw: unknown): ScopeSpecJson {
  const defaults: ScopeSpecJson = {
    summary: '',
    constraints_note: '',
    wbs_rel: null,
    roadmap_rel: null,
    roadmap_section_id: null,
    scope_boundary: 'full_plan',
    milestone_ref: '',
    wbe_path: '',
    capability_label: '',
    team_label: '',
    repo_paths: [],
    recheck_issue_refs: '',
    closure_options: [],
  }
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return { ...defaults }
  const o = raw as Record<string, unknown>
  const repoPaths: string[] = []
  if (Array.isArray(o.repo_paths)) {
    for (const p of o.repo_paths) {
      if (typeof p === 'string') {
        const s = p.trim().slice(0, 2000)
        if (s) repoPaths.push(s)
      }
    }
  }
  return {
    summary: coerceStr(o.summary).slice(0, 8000),
    constraints_note: coerceStr(o.constraints_note).slice(0, 8000),
    wbs_rel: coerceOptStr(o.wbs_rel),
    roadmap_rel: coerceOptStr(o.roadmap_rel),
    roadmap_section_id: o.roadmap_section_id !== undefined ? coerceOptStr(o.roadmap_section_id) : null,
    scope_boundary: coerceScopeBoundary(o.scope_boundary),
    milestone_ref: coerceStr(o.milestone_ref).slice(0, 2000),
    wbe_path: coerceStr(o.wbe_path).slice(0, 4000),
    capability_label: coerceStr(o.capability_label).slice(0, 2000),
    team_label: coerceStr(o.team_label).slice(0, 2000),
    repo_paths: repoPaths,
    recheck_issue_refs: coerceStr(o.recheck_issue_refs).slice(0, 8000),
    closure_options: normalizeClosureOptionsList(o.closure_options),
  }
}

export function normalizeRunPlanStep(raw: unknown): RunPlanJson['steps'][0] | null {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null
  const o = raw as Record<string, unknown>
  const id = coerceStr(o.id).slice(0, 128) || newEntryId()
  return {
    id,
    title: coerceStr(o.title).slice(0, 500),
    detail: coerceStr(o.detail).slice(0, 8000),
  }
}

export function normalizeRunPlan(raw: unknown): RunPlanJson {
  const defaults: RunPlanJson = { id: '', title: '', steps: [] }
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return { ...defaults }
  const o = raw as Record<string, unknown>
  const id = coerceStr(o.id).slice(0, 128) || newEntryId()
  const title = coerceStr(o.title).slice(0, 500)
  const steps: RunPlanJson['steps'] = []
  if (Array.isArray(o.steps)) {
    for (const s of o.steps) {
      const n = normalizeRunPlanStep(s)
      if (n) steps.push(n)
    }
  }
  return { id, title, steps }
}

export function normalizeReviewGate(raw: unknown): ReviewGateJson | null {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null
  const o = raw as Record<string, unknown>
  const id = coerceStr(o.id).slice(0, 128) || newEntryId()
  const passed = typeof o.passed === 'boolean' ? o.passed : false
  return {
    id,
    title: coerceStr(o.title).slice(0, 500),
    passed,
    notes: coerceStr(o.notes).slice(0, 8000),
  }
}

export function normalizeReviewGates(raw: unknown): ReviewGateJson[] {
  if (!Array.isArray(raw)) return []
  const out: ReviewGateJson[] = []
  for (const g of raw) {
    const n = normalizeReviewGate(g)
    if (n) out.push(n)
  }
  return out
}

const RECHECK_LABEL_SET = new Set<string>(RECHECK_PRIMARY_LABELS)

function emptyRecheckReport(): RecheckReportJson {
  return {
    schema_version: 1,
    computed_at: '',
    artifacts: [],
    buckets: [],
    recommendations: {
      regenerate_keys: [],
      approve_first: [],
      unlock_or_request_changes: [],
      flag_for_review: [],
    },
  }
}

export function normalizeRecheckReport(raw: unknown): RecheckReportJson {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return emptyRecheckReport()
  const o = raw as Record<string, unknown>
  const sv = typeof o.schema_version === 'number' && Number.isFinite(o.schema_version) ? Math.max(1, o.schema_version) : 1
  const artifacts: RecheckArtifactRowJson[] = []
  if (Array.isArray(o.artifacts)) {
    for (const row of o.artifacts.slice(0, 128)) {
      if (!row || typeof row !== 'object' || Array.isArray(row)) continue
      const r = row as Record<string, unknown>
      let pl = coerceStr(r.primary_label).slice(0, 32)
      if (!RECHECK_LABEL_SET.has(pl)) pl = 'missing'
      const reasons: string[] = []
      if (Array.isArray(r.reasons)) {
        for (const x of r.reasons.slice(0, 32)) {
          if (typeof x === 'string') {
            const t = x.trim().slice(0, 2000)
            if (t) reasons.push(t)
          }
        }
      }
      artifacts.push({
        artifact_key: coerceStr(r.artifact_key).slice(0, 128),
        primary_label: pl,
        reasons,
        review_status: coerceStr(r.review_status).slice(0, 64),
        generation_id: coerceStr(r.generation_id).slice(0, 128),
        created_at: coerceStr(r.created_at).slice(0, 64),
        parent_generation_id: coerceStr(r.parent_generation_id).slice(0, 128),
      })
    }
  }
  const buckets: RecheckBucketJson[] = []
  if (Array.isArray(o.buckets)) {
    for (const b of o.buckets.slice(0, 8)) {
      if (!b || typeof b !== 'object' || Array.isArray(b)) continue
      const bx = b as Record<string, unknown>
      let wl = coerceStr(bx.worst_label).slice(0, 32)
      if (!RECHECK_LABEL_SET.has(wl)) wl = 'present'
      const artifact_keys: string[] = []
      if (Array.isArray(bx.artifact_keys)) {
        for (const x of bx.artifact_keys.slice(0, 64)) {
          if (typeof x === 'string') {
            const s = x.trim().slice(0, 128)
            if (s) artifact_keys.push(s)
          }
        }
      }
      buckets.push({
        id: coerceStr(bx.id).slice(0, 32),
        worst_label: wl,
        artifact_keys,
      })
    }
  }
  const rec = o.recommendations
  const recommendations: RecheckRecommendationsJson = {
    regenerate_keys: [],
    approve_first: [],
    unlock_or_request_changes: [],
    flag_for_review: [],
  }
  if (rec && typeof rec === 'object' && !Array.isArray(rec)) {
    const rr = rec as Record<string, unknown>
    for (const fld of ['regenerate_keys', 'approve_first', 'unlock_or_request_changes'] as const) {
      const lst = rr[fld]
      if (Array.isArray(lst)) {
        for (const x of lst.slice(0, 64)) {
          if (typeof x === 'string') {
            const s = x.trim().slice(0, 128)
            if (s) recommendations[fld].push(s)
          }
        }
      }
    }
    if (Array.isArray(rr.flag_for_review)) {
      for (const x of rr.flag_for_review.slice(0, 64)) {
        if (typeof x === 'string') {
          const t = x.trim().slice(0, 4000)
          if (t) recommendations.flag_for_review.push(t)
        }
      }
    }
  }
  return {
    schema_version: sv,
    computed_at: coerceStr(o.computed_at).slice(0, 64),
    artifacts,
    buckets,
    recommendations,
  }
}

export function normalizeRecheckSummary(raw: unknown): RecheckSummaryJson {
  const defaults: RecheckSummaryJson = { checked_at: '', passed: false, issues: [], report: emptyRecheckReport() }
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return { ...defaults }
  const o = raw as Record<string, unknown>
  const issues: string[] = []
  if (Array.isArray(o.issues)) {
    for (const x of o.issues) {
      if (typeof x === 'string') {
        const t = x.trim().slice(0, 2000)
        if (t) issues.push(t)
      }
    }
  }
  return {
    checked_at: coerceStr(o.checked_at).slice(0, 64),
    passed: typeof o.passed === 'boolean' ? o.passed : false,
    issues,
    report: normalizeRecheckReport(o.report),
  }
}

export function normalizeBuildPackPlan(raw: unknown): BuildPackPlanJson {
  const defaults: BuildPackPlanJson = {
    format: 'json',
    paths: [],
    notes: '',
    allowed_write_globs: [],
    guardrail_notes: '',
  }
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return { ...defaults }
  const o = raw as Record<string, unknown>
  const paths: string[] = []
  if (Array.isArray(o.paths)) {
    for (const p of o.paths) {
      if (typeof p === 'string') {
        const s = p.trim().slice(0, 2000)
        if (s) paths.push(s)
      }
    }
  }
  const globs: string[] = []
  if (Array.isArray(o.allowed_write_globs)) {
    for (const g of o.allowed_write_globs) {
      if (typeof g === 'string') {
        const t = g.trim().slice(0, 500)
        if (t) globs.push(t)
      }
    }
  }
  const fmt = coerceStr(o.format).slice(0, 64) || 'json'
  return {
    format: fmt,
    paths,
    notes: coerceStr(o.notes).slice(0, 8000),
    allowed_write_globs: globs.slice(0, 64),
    guardrail_notes: coerceStr(o.guardrail_notes).slice(0, 8000),
  }
}

export function normalizePromptRecipe(raw: unknown): PromptRecipeJson {
  const defaults: PromptRecipeJson = {
    recipe_id: '',
    intent: 'clarify',
    template_ref: '',
    variables: {},
    prompt_mode: 'static',
    materialization_inputs: [],
    placeholder_summary: '',
  }
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return { ...defaults }
  const o = raw as Record<string, unknown>
  const variables: Record<string, string> = {}
  if (o.variables && typeof o.variables === 'object' && !Array.isArray(o.variables)) {
    for (const [kk, vv] of Object.entries(o.variables as Record<string, unknown>)) {
      const key = coerceStr(kk).slice(0, 120)
      if (!key) continue
      variables[key] = coerceStr(vv).slice(0, 4000)
    }
  }
  const materialization_inputs: string[] = []
  if (Array.isArray(o.materialization_inputs)) {
    for (const x of o.materialization_inputs) {
      if (typeof x === 'string') {
        const t = x.trim().slice(0, 500)
        if (t) materialization_inputs.push(t)
      }
    }
  }
  return {
    recipe_id: coerceStr(o.recipe_id).slice(0, 200),
    intent: coerceEnum(o.intent, PROMPT_INTENTS, 'clarify'),
    template_ref: coerceStr(o.template_ref).slice(0, 500),
    variables,
    prompt_mode: coerceEnum(o.prompt_mode, PROMPT_MODES, 'static'),
    materialization_inputs: materialization_inputs.slice(0, 64),
    placeholder_summary: coerceStr(o.placeholder_summary).slice(0, 4000),
  }
}

export function normalizePromptSnapshot(raw: unknown): PromptSnapshotJson | null {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null
  const o = raw as Record<string, unknown>
  return {
    snapshot_id: coerceStr(o.snapshot_id).slice(0, 128) || newEntryId(),
    recipe_id: coerceStr(o.recipe_id).slice(0, 200),
    rendered: coerceStr(o.rendered).slice(0, 200_000),
    content_hash: coerceStr(o.content_hash).slice(0, 128),
    created_at: coerceStr(o.created_at).slice(0, 64),
  }
}

export function normalizeArtifactStatusMap(raw: unknown): Record<string, string> {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return {}
  const out: Record<string, string> = {}
  for (const [k, v] of Object.entries(raw as Record<string, unknown>)) {
    const key = coerceStr(k).slice(0, 200)
    if (!key) continue
    out[key] = coerceEnum(v, ARTIFACT_STATUSES, 'missing')
  }
  return out
}

function clamp01(v: unknown): number {
  const x = typeof v === 'number' ? v : parseFloat(String(v))
  if (!Number.isFinite(x) || x !== x) return 0
  return Math.max(0, Math.min(1, x))
}

function normalizeQualityDimensionEntry(raw: unknown): QualityDimensionScoreJson {
  const defaults: QualityDimensionScoreJson = { score: 0, rationale: '' }
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return { ...defaults }
  const o = raw as Record<string, unknown>
  return {
    score: clamp01(o.score),
    rationale: coerceStr(o.rationale).slice(0, 4000),
  }
}

export function normalizeQualityRubric(raw: unknown): QualityRubricJson {
  const out: QualityRubricJson = {} as QualityRubricJson
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    for (const dim of QUALITY_DIMENSIONS) {
      out[dim] = normalizeQualityDimensionEntry({})
    }
    return out
  }
  const o = raw as Record<string, unknown>
  for (const dim of QUALITY_DIMENSIONS) {
    out[dim] = normalizeQualityDimensionEntry(o[dim])
  }
  return out
}

function normalizeLineageUpstream(raw: unknown): ArtifactLineageUpstreamJson[] {
  if (!Array.isArray(raw)) return []
  const out: ArtifactLineageUpstreamJson[] = []
  for (const item of raw.slice(0, 32)) {
    if (!item || typeof item !== 'object' || Array.isArray(item)) continue
    const o = item as Record<string, unknown>
    const ak = coerceStr(o.artifact_key).slice(0, 64)
    const gid = coerceStr(o.generation_id).slice(0, 128)
    if (!ak || !gid) continue
    out.push({
      artifact_key: ak,
      generation_id: gid,
      review_status: coerceEnum(o.review_status, ARTIFACT_REVIEW_STATUSES, 'pending'),
    })
  }
  return out
}

function normalizeLineage(raw: unknown): ArtifactLineageJson {
  const defaults: ArtifactLineageJson = { upstream: [] }
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return defaults
  const o = raw as Record<string, unknown>
  return { upstream: normalizeLineageUpstream(o.upstream) }
}

function normalizeProvenance(raw: unknown): GeneratedArtifactRecordJson['provenance'] {
  const defaults = {
    generation_id: '',
    created_at: '',
    provider: '',
    model: '',
    input_fingerprint: '',
    parent_generation_id: '',
    lineage: { upstream: [] as ArtifactLineageUpstreamJson[] },
  }
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    return { ...defaults, generation_id: newEntryId() }
  }
  const o = raw as Record<string, unknown>
  return {
    generation_id: coerceStr(o.generation_id).slice(0, 128) || newEntryId(),
    created_at: coerceStr(o.created_at).slice(0, 64),
    provider: coerceStr(o.provider).slice(0, 64),
    model: coerceStr(o.model).slice(0, 200),
    input_fingerprint: coerceStr(o.input_fingerprint).slice(0, 128),
    parent_generation_id: coerceStr(o.parent_generation_id).slice(0, 128),
    lineage: normalizeLineage(o.lineage),
  }
}

function normalizeGeneratedArtifactRecord(
  _sliceKey: (typeof ARTIFACT_SLICE_KEYS)[number],
  raw: unknown,
): GeneratedArtifactRecordJson | null {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null
  const o = raw as Record<string, unknown>
  const locked = o.locked === true
  let reviewStatus = coerceEnum(o.review_status, ARTIFACT_REVIEW_STATUSES, 'pending')
  if (locked) reviewStatus = 'locked'
  return {
    content: (o.content && typeof o.content === 'object' && !Array.isArray(o.content)
      ? (o.content as Record<string, unknown>)
      : {}) as Record<string, unknown>,
    quality: normalizeQualityRubric(o.quality),
    review_status: reviewStatus,
    locked,
    feedback: coerceStr(o.feedback).slice(0, 8000),
    provenance: normalizeProvenance(o.provenance),
  }
}

export function normalizeArtifactGeneration(raw: unknown): ArtifactGenerationJson {
  const defaults: ArtifactGenerationJson = { schema_version: 2, artifacts: {} }
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return { ...defaults }
  const o = raw as Record<string, unknown>
  const sv = coerceSchemaVersion(o.schema_version)
  const artifacts: Partial<Record<(typeof ARTIFACT_SLICE_KEYS)[number], GeneratedArtifactRecordJson>> = {}
  const ar = o.artifacts
  if (ar && typeof ar === 'object' && !Array.isArray(ar)) {
    for (const key of ARTIFACT_SLICE_KEYS) {
      const rec = normalizeGeneratedArtifactRecord(key, (ar as Record<string, unknown>)[key])
      if (rec) artifacts[key] = rec
    }
  }
  return { schema_version: sv, artifacts }
}

export function emptyWizardDomain(): WizardDomainJson {
  return {
    schema_version: 1,
    mission_type: 'explore',
    contribution_setup_kind: 'single',
    context_sources: [],
    foundation_brief: normalizeFoundationBrief({}),
    assumption_ledger: [],
    artifact_packs: [],
    target_stage: 'idea',
    autonomy_level: 'l0_analyst',
    mutation_policy: 'read_only_analysis',
    scope_spec: normalizeScopeSpec({}),
    run_plan: normalizeRunPlan({}),
    review_gates: normalizeReviewGates([]),
    artifact_status_by_id: {},
    recheck_summary: normalizeRecheckSummary({}),
    build_pack_plan: normalizeBuildPackPlan({}),
    prompt_recipe: normalizePromptRecipe({}),
    prompt_snapshot: null,
    artifact_generation: normalizeArtifactGeneration({}),
  }
}

export function normalizeWizardDomain(raw: unknown): WizardDomainJson {
  const defaults = emptyWizardDomain()
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    return JSON.parse(JSON.stringify(defaults)) as WizardDomainJson
  }

  const preserved: Record<string, unknown> = {}
  const r = raw as Record<string, unknown>
  for (const [k, v] of Object.entries(r)) {
    if (!(k in defaults)) preserved[k] = v
  }

  const out: WizardDomainJson = { ...defaults }
  for (const key of Object.keys(defaults) as (keyof WizardDomainJson)[]) {
    if (key === 'schema_version') continue
    if (key in r) {
      ;(out as Record<string, unknown>)[key as string] = r[key as string]
    }
  }

  out.schema_version = coerceSchemaVersion(r.schema_version)

  out.mission_type = coerceEnum(r.mission_type, MISSION_TYPES, 'explore')
  out.contribution_setup_kind = coerceEnum(r.contribution_setup_kind, CONTRIBUTION_SETUP_KINDS, 'single')

  const sources: string[] = []
  if (Array.isArray(r.context_sources)) {
    for (const x of r.context_sources) sources.push(coerceEnum(x, CONTEXT_SOURCES, 'other'))
  }
  out.context_sources = sources

  out.foundation_brief = normalizeFoundationBrief(r.foundation_brief)
  out.assumption_ledger = normalizeAssumptionLedger(r.assumption_ledger)

  const packs: ArtifactPackJson[] = []
  if (Array.isArray(r.artifact_packs)) {
    for (const p of r.artifact_packs) packs.push(normalizeArtifactPack(p))
  }
  out.artifact_packs = packs

  out.target_stage = coerceTargetStage(r.target_stage)
  out.autonomy_level = coerceAutonomyLevel(r.autonomy_level)
  out.mutation_policy = coerceMutationPolicy(r.mutation_policy)

  out.scope_spec = normalizeScopeSpec(r.scope_spec)
  out.run_plan = normalizeRunPlan(r.run_plan)
  out.review_gates = normalizeReviewGates(r.review_gates)
  out.artifact_status_by_id = normalizeArtifactStatusMap(r.artifact_status_by_id)
  out.recheck_summary = normalizeRecheckSummary(r.recheck_summary)
  out.build_pack_plan = normalizeBuildPackPlan(r.build_pack_plan)
  out.prompt_recipe = normalizePromptRecipe(r.prompt_recipe)

  if (r.prompt_snapshot === null || r.prompt_snapshot === undefined) {
    out.prompt_snapshot = null
  } else {
    out.prompt_snapshot = normalizePromptSnapshot(r.prompt_snapshot)
  }

  out.artifact_generation = normalizeArtifactGeneration(r.artifact_generation)

  Object.assign(out, preserved)
  out.schema_version = coerceSchemaVersion(r.schema_version)
  return out
}
