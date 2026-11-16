import { describe, expect, it } from 'vitest'
import type { DocsHealthSessionPayload } from '../api/docsHealth'
import type { ForgeWorkflowStage } from '../forgesdlc-kitchensink'
import {
  buildDocsHealthWorkflowStages,
  deriveDefaultWorkflowTab,
  mapBackendStepToWorkflowStage,
  proposedKindToArtifactTab,
  resolveWorkflowStageAttentionStageId,
  WORKFLOW_STAGE_ORDER,
} from './docsHealthStageFlow'

function sess(p: Partial<DocsHealthSessionPayload>): DocsHealthSessionPayload {
  return p as DocsHealthSessionPayload
}

describe('mapBackendStepToWorkflowStage', () => {
  it('maps triage and draft family to workflow tabs', () => {
    expect(mapBackendStepToWorkflowStage('cluster_brief')).toBe('analyze')
    expect(mapBackendStepToWorkflowStage('enrich')).toBe('gather')
    expect(mapBackendStepToWorkflowStage('draft')).toBe('draft')
    expect(mapBackendStepToWorkflowStage('diagram_draft')).toBe('draft')
    expect(mapBackendStepToWorkflowStage('decision_stub')).toBe('draft')
    expect(mapBackendStepToWorkflowStage('review')).toBe('review')
    expect(mapBackendStepToWorkflowStage('apply')).toBe('apply')
    expect(mapBackendStepToWorkflowStage('verify')).toBe('verify')
  })
})

describe('proposedKindToArtifactTab', () => {
  it('maps patch kinds to draft artifact tabs', () => {
    expect(proposedKindToArtifactTab(undefined)).toBe('patch')
    expect(proposedKindToArtifactTab('diagram')).toBe('diagram')
    expect(proposedKindToArtifactTab('adr')).toBe('adr')
    expect(proposedKindToArtifactTab('ADR')).toBe('adr')
  })
})

describe('deriveDefaultWorkflowTab', () => {
  it('prefers attention statuses in order', () => {
    const stages: ForgeWorkflowStage[] = WORKFLOW_STAGE_ORDER.map((id) => ({
      id,
      label: id,
      status: 'not_started',
    }))
    stages[2] = { ...stages[2], status: 'failed' }
    expect(deriveDefaultWorkflowTab(stages)).toBe(stages[2].id)
  })

  it('falls back to first not_started', () => {
    const stages = WORKFLOW_STAGE_ORDER.map((id) => ({
      id,
      label: id,
      status: id === 'gather' ? ('not_started' as const) : ('completed' as const),
    }))
    expect(deriveDefaultWorkflowTab(stages)).toBe('gather')
  })

  it('defaults to last stage when all complete', () => {
    const stages = WORKFLOW_STAGE_ORDER.map((id) => ({
      id,
      label: id,
      status: 'completed' as const,
    }))
    expect(deriveDefaultWorkflowTab(stages)).toBe('verify')
  })
})

describe('buildDocsHealthWorkflowStages', () => {
  it('marks all backend stages completed when session status is completed', () => {
    const stages = buildDocsHealthWorkflowStages(sess({ status: 'completed' }), null)
    expect(stages.every((s) => s.status === 'completed')).toBe(true)
  })

  it('exposes draft merge: any draft substep completed marks draft workflow stage', () => {
    const stages = buildDocsHealthWorkflowStages(
      sess({
        status: 'running',
        step_metrics: [{ step: 'draft' }],
      }),
      null,
    )
    const draft = stages.find((s) => s.id === 'draft')
    expect(draft?.status).toBe('completed')
  })

  it('respects busy step as in_progress', () => {
    const stages = buildDocsHealthWorkflowStages(sess({ status: 'running', step_metrics: [] }), 'review')
    const review = stages.find((s) => s.id === 'review')
    expect(review?.status).toBe('in_progress')
  })

  it('anchors idle open run on Summary (blocked) so progress strip is not all blank', () => {
    const stages = buildDocsHealthWorkflowStages(sess({ status: 'running', step_metrics: [] }), null)
    expect(stages.find((s) => s.id === 'analyze')?.status).toBe('blocked')
    expect(stages.filter((s) => s.id !== 'analyze').every((s) => s.status === 'not_started')).toBe(true)
    expect(resolveWorkflowStageAttentionStageId(stages)).toBe('analyze')
  })

  it('does not anchor idle when a step is busy even if step_metrics is still empty', () => {
    const stages = buildDocsHealthWorkflowStages(sess({ status: 'running', step_metrics: [] }), 'review')
    expect(stages.find((s) => s.id === 'analyze')?.status).toBe('not_started')
    expect(resolveWorkflowStageAttentionStageId(stages)).toBe('review')
  })
})
