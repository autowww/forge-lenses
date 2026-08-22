import type { DocsHealthSessionPayload } from '../api/docsHealth'
import type { ForgeWorkflowStage, ForgeWorkflowStageStatus } from '../forgesdlc-kitchensink'
import { DOCS_HEALTH_PIPELINE_STEP_LABELS as PL, DOCS_HEALTH_PIPELINE_STEP_SHORT as PS } from './docsHealthStepLabels'

export type StageId =
  | 'cluster_brief'
  | 'enrich'
  | 'draft'
  | 'diagram_draft'
  | 'decision_stub'
  | 'review'
  | 'apply'
  | 'verify'

/** Six user-facing workflow stages (process), distinct from backend step ids and draft artifacts. */
export type WorkflowStageId = 'analyze' | 'gather' | 'draft' | 'review' | 'apply' | 'verify'

export const WORKFLOW_STAGE_ORDER: readonly WorkflowStageId[] = [
  'analyze',
  'gather',
  'draft',
  'review',
  'apply',
  'verify',
] as const

export const WORKFLOW_STAGE_LABELS: Record<WorkflowStageId, string> = {
  analyze: 'Summary',
  gather: 'Gather context',
  draft: 'Draft documentation',
  review: 'Review and policy checks',
  apply: 'Approve and apply to branch',
  verify: 'Re-scan and verify',
}

export type StageGroup = 'triage' | 'draft' | 'ship'

export const DOCS_HEALTH_STAGE_DEFS: ReadonlyArray<{
  id: StageId
  label: string
  short: string
  group: StageGroup
}> = [
  { id: 'cluster_brief', label: PL.cluster_brief, short: PS.cluster_brief, group: 'triage' },
  { id: 'enrich', label: PL.enrich, short: PS.enrich, group: 'triage' },
  { id: 'draft', label: PL.draft, short: PS.draft, group: 'draft' },
  { id: 'diagram_draft', label: PL.diagram_draft, short: PS.diagram_draft, group: 'draft' },
  { id: 'decision_stub', label: PL.decision_stub, short: PS.decision_stub, group: 'draft' },
  { id: 'review', label: PL.review, short: PS.review, group: 'ship' },
  { id: 'apply', label: PL.apply, short: PS.apply, group: 'ship' },
  { id: 'verify', label: PL.verify, short: PS.verify, group: 'ship' },
]

const PRI: Record<ForgeWorkflowStageStatus, number> = {
  failed: 100,
  in_progress: 90,
  waiting: 85,
  blocked: 82,
  cancelled: 70,
  completed: 50,
  skipped: 45,
  not_started: 0,
}

function maxStatusByPriority(statuses: ForgeWorkflowStageStatus[]): ForgeWorkflowStageStatus {
  return statuses.reduce((a, b) => (PRI[b] > PRI[a] ? b : a), 'not_started' as ForgeWorkflowStageStatus)
}

export function aggregateStepMetrics(
  rows: DocsHealthSessionPayload['step_metrics'] | undefined,
): Record<string, { prompt_tokens: number; completion_tokens: number; total_tokens: number; elapsed_ms: number; runs: number }> {
  const out: Record<
    string,
    { prompt_tokens: number; completion_tokens: number; total_tokens: number; elapsed_ms: number; runs: number }
  > = {}
  for (const r of rows || []) {
    const sid = String(r?.step || '').trim()
    if (!sid) continue
    if (!out[sid]) {
      out[sid] = { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0, elapsed_ms: 0, runs: 0 }
    }
    out[sid].prompt_tokens += Number(r?.prompt_tokens) || 0
    out[sid].completion_tokens += Number(r?.completion_tokens) || 0
    out[sid].total_tokens += Number(r?.total_tokens) || 0
    out[sid].elapsed_ms += Number(r?.elapsed_ms) || 0
    out[sid].runs += 1
  }
  return out
}

/**
 * Which pipeline stage is waiting on the operator (reply or approval).
 */
export function resolveBlockedStageId(session: Pick<DocsHealthSessionPayload, 'status' | 'proposed_patch_kind' | 'step_metrics'>): StageId | null {
  const st = String(session.status || '').toLowerCase()
  if (st === 'awaiting_approval') {
    const k = String(session.proposed_patch_kind || '').toLowerCase()
    if (k === 'diagram') return 'diagram_draft'
    if (k === 'adr') return 'decision_stub'
    return 'draft'
  }
  if (st === 'awaiting_input') {
    const metrics = [...(session.step_metrics || [])].reverse()
    const g = metrics.find((m) => m?.gate === 'awaiting_input')
    if (g?.step && isStageId(g.step)) {
      return g.step
    }
    const last = metrics.find((m) => m?.step)
    if (last?.step && isStageId(last.step)) {
      return last.step
    }
    return 'draft'
  }
  return null
}

function isStageId(s: string): s is StageId {
  return DOCS_HEALTH_STAGE_DEFS.some((d) => d.id === s)
}

export function fmtStageDuration(ms: number): string {
  if (!ms || ms < 0) return '—'
  if (ms < 1000) return `${ms} ms`
  const s = Math.round(ms / 1000)
  if (s < 60) return `${s}s`
  const m = Math.floor(s / 60)
  const rs = s % 60
  return `${m}m ${rs}s`
}

export function fmtStageTokens(n: number): string {
  if (!n || n < 0) return '—'
  return n.toLocaleString()
}

/**
 * Maps a backend step to the user-facing workflow stage (draft artifacts share the "draft" stage).
 */
export function mapBackendStepToWorkflowStage(step: StageId): WorkflowStageId {
  switch (step) {
    case 'cluster_brief':
      return 'analyze'
    case 'enrich':
      return 'gather'
    case 'draft':
    case 'diagram_draft':
    case 'decision_stub':
      return 'draft'
    case 'review':
      return 'review'
    case 'apply':
      return 'apply'
    case 'verify':
      return 'verify'
  }
}

export function proposedKindToArtifactTab(kind?: string | null): 'patch' | 'diagram' | 'adr' {
  const k = String(kind || '').toLowerCase()
  if (k === 'diagram') return 'diagram'
  if (k === 'adr') return 'adr'
  return 'patch'
}

function computeBackendStageStatuses(
  session: Pick<DocsHealthSessionPayload, 'status' | 'step_metrics' | 'proposed_patch_kind'> | null | undefined,
  busyStep: string | null | undefined,
): Record<StageId, ForgeWorkflowStageStatus> {
  const st = String(session?.status || '').toLowerCase()
  const agg = aggregateStepMetrics(session?.step_metrics)
  const blocked = session ? resolveBlockedStageId(session) : null
  const out = {} as Record<StageId, ForgeWorkflowStageStatus>

  for (const def of DOCS_HEALTH_STAGE_DEFS) {
    const id = def.id
    const hasRun = (agg[id]?.runs ?? 0) > 0
    let status: ForgeWorkflowStageStatus = 'not_started'

    if (st === 'completed') {
      status = 'completed'
    } else if (st === 'cancelled') {
      status = hasRun ? 'completed' : 'cancelled'
    } else if (st === 'failed') {
      if (busyStep === id) status = 'failed'
      else if (hasRun) status = 'completed'
      else status = 'not_started'
    } else {
      if (blocked === id) status = 'waiting'
      else if (busyStep === id) status = 'in_progress'
      else if (hasRun) status = 'completed'
      // else: remain `not_started` — session.status is often "running" as soon as the run exists,
      // but LLM steps only start after session_step (see busyStep / step_metrics).
    }

    out[id] = status
  }

  if (st === 'paused' && blocked && out[blocked] === 'waiting') {
    out[blocked] = 'blocked'
  }

  return out
}

/**
 * User-facing remediation lifecycle for ForgeWorkflowStageBar + tab navigation.
 * Backend draft/diagram/ADR steps are merged into a single "Draft changes" stage.
 */
export function buildDocsHealthWorkflowStages(
  session: Pick<DocsHealthSessionPayload, 'status' | 'step_metrics' | 'proposed_patch_kind'> | null | undefined,
  busyStep: string | null | undefined,
): ForgeWorkflowStage[] {
  const bs = computeBackendStageStatuses(session, busyStep)
  const draftMerged = maxStatusByPriority([bs.draft, bs.diagram_draft, bs.decision_stub])

  const stages = WORKFLOW_STAGE_ORDER.map((wid) => {
    let status: ForgeWorkflowStageStatus
    switch (wid) {
      case 'analyze':
        status = bs.cluster_brief
        break
      case 'gather':
        status = bs.enrich
        break
      case 'draft':
        status = draftMerged
        break
      case 'review':
        status = bs.review
        break
      case 'apply':
        status = bs.apply
        break
      case 'verify':
        status = bs.verify
        break
    }
    return { id: wid, label: WORKFLOW_STAGE_LABELS[wid], status }
  })

  /** Session is live but no pipeline invocation yet — anchor attention on Summary so tiles/track are not all blank. */
  const st = String(session?.status || '').toLowerCase()
  const metricsEmpty = !(session?.step_metrics && session.step_metrics.length > 0)
  if ((st === 'running' || st === 'paused') && !busyStep && metricsEmpty) {
    return stages.map((s) =>
      s.id === 'analyze' && s.status === 'not_started' ? { ...s, status: 'blocked' as const } : s,
    )
  }

  return stages
}

/**
 * Workflow tile + progress tick that should read as “where attention is” (agent step, human gate, or idle-at-start).
 */
export function resolveWorkflowStageAttentionStageId(stages: ForgeWorkflowStage[]): string | null {
  const hit = stages.find((s) => ['in_progress', 'waiting', 'blocked'].includes(s.status))
  return hit?.id ?? null
}

/**
 * Picks a sensible default tab from live session + stage strip (attention first).
 */
export function deriveDefaultWorkflowTab(stages: ForgeWorkflowStage[]): WorkflowStageId {
  const attention: ForgeWorkflowStageStatus[] = ['failed', 'blocked', 'waiting', 'in_progress']
  for (const a of attention) {
    const hit = stages.find((s) => s.status === a)
    if (hit && isWorkflowStageId(hit.id)) return hit.id
  }
  const notStarted = stages.find((s) => s.status === 'not_started')
  if (notStarted && isWorkflowStageId(notStarted.id)) return notStarted.id
  const last = stages[stages.length - 1]
  return isWorkflowStageId(last?.id) ? last.id : 'verify'
}

function isWorkflowStageId(s: string): s is WorkflowStageId {
  return (WORKFLOW_STAGE_ORDER as readonly string[]).includes(s)
}
