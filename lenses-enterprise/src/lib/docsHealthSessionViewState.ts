import type { ReactNode } from 'react'
import type { DocsHealthSessionPayload } from '../api/docsHealth'
import type { ForgeStatusBannerVariant } from '../forgesdlc-kitchensink/forgeRunTypes'
import { aggregateStepMetrics, type StageId } from './docsHealthStageFlow'

/**
 * UI view state for the remediation run console (maps API status + payload; not identical to raw `session.status`).
 */
export type RemediationViewState =
  | 'loading'
  | 'running'
  | 'awaiting_input'
  | 'awaiting_approval'
  | 'applied_await_verify'
  | 'verified'
  | 'cancelled'
  | 'failed'

export function hasReviewableChange(session: DocsHealthSessionPayload | null): boolean {
  if (!session) return false
  if (session.proposed_patch?.content || session.proposed_patch?.path) return true
  if (session.patch_preview?.apply_ready === true || session.patch_preview?.apply_artifact) return true
  return Boolean(session.events?.some((e) => e.type === 'diff' && (e.unified || e.path)))
}

/** Apply step has run but verify step has not (status still in-flight). */
export function hasAppliedAwaitingVerify(session: DocsHealthSessionPayload | null): boolean {
  if (!session) return false
  const st = String(session.status || '').toLowerCase()
  if (st === 'completed' || st === 'cancelled' || st === 'failed') return false
  const agg = aggregateStepMetrics(session.step_metrics)
  const applyRuns = agg.apply?.runs ?? 0
  const verifyRuns = agg.verify?.runs ?? 0
  return applyRuns > 0 && verifyRuns === 0
}

/** Heuristic: cancel persisted before any apply side-effects in metrics. */
export function likelyNoAppliedChangesOnCancel(session: DocsHealthSessionPayload | null): boolean {
  if (!session) return true
  const agg = aggregateStepMetrics(session.step_metrics)
  const applyRuns = agg.apply?.runs ?? 0
  const files = session.header_stats?.files_changed ?? 0
  return applyRuns === 0 && files === 0
}

export function deriveRemediationViewState(session: DocsHealthSessionPayload | null): RemediationViewState {
  if (!session) return 'loading'
  const st = String(session.status || '').toLowerCase()
  if (st === 'cancelled') return 'cancelled'
  if (st === 'failed') return 'failed'
  if (st === 'awaiting_input') return 'awaiting_input'
  if (st === 'awaiting_approval') return 'awaiting_approval'
  if (st === 'completed') return 'verified'
  if (st === 'running' || st === 'paused') {
    if (hasAppliedAwaitingVerify(session)) return 'applied_await_verify'
    return 'running'
  }
  return 'running'
}

export function inferRetryStep(session: DocsHealthSessionPayload | null): StageId {
  const rows = session?.step_metrics ?? []
  for (let i = rows.length - 1; i >= 0; i--) {
    const s = String(rows[i]?.step || '').trim()
    if (isStageId(s)) return s
  }
  return 'verify'
}

function isStageId(s: string): s is StageId {
  return (
    s === 'cluster_brief' ||
    s === 'enrich' ||
    s === 'draft' ||
    s === 'diagram_draft' ||
    s === 'decision_stub' ||
    s === 'review' ||
    s === 'apply' ||
    s === 'verify'
  )
}

export type RemediationBannerMessage = {
  variant: ForgeStatusBannerVariant
  title: string
  description: ReactNode
}

/** State-driven banner copy (primary message above the fold). */
export function getRemediationBannerMessage(
  view: RemediationViewState,
  session: DocsHealthSessionPayload | null,
  opts: { hasReviewable: boolean; cancelledNoApplyChanges: boolean },
): RemediationBannerMessage | null {
  if (view === 'loading' || !session) return null

  if (view === 'cancelled') {
    const inFlight =
      'Cancellation is saved: no new stages will start. One in-flight request may still finish—check Run activity for details.'
    if (opts.cancelledNoApplyChanges) {
      return {
        variant: 'cancelled',
        title: 'Run cancelled',
        description: `This run was cancelled before changes were applied. ${inFlight}`,
      }
    }
    return {
      variant: 'cancelled',
      title: 'Run cancelled',
      description: `The run was stopped. ${inFlight} Review Run activity if you expected changes to land before cancel.`,
    }
  }

  if (view === 'failed') {
    return {
      variant: 'failed',
      title: 'Run failed',
      description:
        'Open Run activity to see which step failed. Retry the last stage or adjust inputs, then run again when ready.',
    }
  }

  if (view === 'awaiting_approval') {
    if (!opts.hasReviewable) {
      return {
        variant: 'awaiting_approval',
        title: 'Waiting for review',
        description:
          'Waiting for review before changes can be applied. Run draft or review steps when you are ready to produce a reviewable proposal.',
      }
    }
    return {
      variant: 'awaiting_approval',
      title: 'Review before apply',
      description:
        'Review proposed changes under Draft documentation, then approve or send back for more work. Use a dedicated branch when one is suggested.',
    }
  }

  if (view === 'awaiting_input') {
    return {
      variant: 'awaiting_input',
      title: 'Your input is needed',
      description: 'Answer the question or add context below so the run can continue.',
    }
  }

  if (view === 'applied_await_verify') {
    return {
      variant: 'warning',
      title: 'Apply completed — verify next',
      description:
        'Verification has not run on the updated documentation yet. Run Re-scan and verify to refresh the score and closure status.',
    }
  }

  if (view === 'verified') {
    const ok = session.completion_summary?.verification_pipeline_ok
    return {
      variant: 'verified',
      title: 'Run complete',
      description:
        ok === false
          ? 'Verification reported issues—see Run activity and project Docs health for details.'
          : 'Verification finished. Open project Docs health to view the updated score and results.',
    }
  }

  /* Status + next steps are in the compact run summary; avoid duplicating a tall banner while running. */
  if (view === 'running') {
    return null
  }

  return null
}
