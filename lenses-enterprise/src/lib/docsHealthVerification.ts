import type { ReactNode } from 'react'
import type {
  DocsHealthProjectPayload,
  DocsHealthScore,
  DocsHealthSessionPayload,
} from '../api/docsHealth'
import type { ForgeStatusBannerVariant } from '../forgesdlc-kitchensink/forgeRunTypes'
import { aggregateStepMetrics } from './docsHealthStageFlow'

export type MergedFindingDiff = {
  resolved: string[]
  newFindings: string[]
  reopened: string[]
}

/**
 * Prefer session completion finding_diff; fall back to latest project scan row when present.
 */
type ApiFindingDiff = {
  resolved_from_prior_scan?: string[]
  new_since_prior_scan?: string[]
  reopened_findings?: string[]
}

export function mergeFindingDiff(
  session: DocsHealthSessionPayload | null,
  project: DocsHealthProjectPayload | null,
): MergedFindingDiff {
  const fd = session?.completion_summary?.finding_diff
  const fdP = (project?.latest_run as { finding_diff?: ApiFindingDiff } | null | undefined)?.finding_diff
  const nor = session?.completion_summary?.findings_new_or_reopened

  if (fd) {
    return {
      resolved: [...(fd.resolved_from_prior_scan ?? [])],
      newFindings: [...(fd.new_since_prior_scan ?? [])],
      reopened: [...(fd.reopened_findings ?? [])],
    }
  }

  if (fdP) {
    return {
      resolved: [...(fdP.resolved_from_prior_scan ?? [])],
      newFindings: [...(fdP.new_since_prior_scan ?? [])],
      reopened: [...(fdP.reopened_findings ?? [])],
    }
  }

  return {
    resolved: [],
    newFindings: [...(nor?.new ?? [])],
    reopened: [...(nor?.reopened ?? [])],
  }
}

export function extractNumericScore(score: unknown): number | null {
  if (score == null) return null
  if (typeof score === 'number' && !Number.isNaN(score)) return score
  if (typeof score === 'object' && score !== null && 'value' in score) {
    const v = (score as DocsHealthScore).value
    return typeof v === 'number' && !Number.isNaN(v) ? v : null
  }
  return null
}

export function scoreObject(score: unknown): DocsHealthScore | null {
  if (score != null && typeof score === 'object' && 'value' in (score as object)) {
    return score as DocsHealthScore
  }
  return null
}

export type VerificationBanner = {
  variant: ForgeStatusBannerVariant
  title: string
  description: ReactNode
  nextAction: string | null
}

/**
 * Primary verification headline for the Verify workflow panel (explicit outcomes; no silent dashes).
 */
export function deriveVerificationBanner(session: DocsHealthSessionPayload | null): VerificationBanner {
  if (!session) {
    return {
      variant: 'info',
      title: 'Session not loaded',
      description: 'Loading run…',
      nextAction: null,
    }
  }

  const st = String(session.status || '').toLowerCase()
  const agg = aggregateStepMetrics(session.step_metrics)
  const applyRuns = agg.apply?.runs ?? 0
  const verifyRuns = agg.verify?.runs ?? 0
  const completion = session.completion_summary
  const vOk = completion?.verification_pipeline_ok

  if (applyRuns === 0 && verifyRuns === 0) {
    return {
      variant: 'info',
      title: 'Verification has not run',
      description: 'Verification has not run because no changes were applied',
      nextAction: 'Approve and apply changes first, then run Re-scan and verify.',
    }
  }

  if (applyRuns === 0 && verifyRuns > 0) {
    return {
      variant: 'info',
      title: 'Verify step recorded without apply',
      description:
        'Metrics show verification without a matching apply step. Results may reference an earlier scan or bookkeeping only.',
      nextAction: 'Confirm outcomes in Run activity and on the latest project scan.',
    }
  }

  if (st === 'failed') {
    return {
      variant: 'failed',
      title: 'Verification failed or incomplete',
      description: 'The run failed before or during verification. Check Run activity for the error.',
      nextAction: 'Resolve the issue, then resume or run Re-scan and verify when the workflow allows.',
    }
  }

  if (st === 'cancelled') {
    if (verifyRuns === 0) {
      return {
        variant: 'cancelled',
        title: 'Verification skipped',
        description: 'This run was stopped before post-apply verification finished.',
        nextAction: 'Resume or start a new remediation run when you are ready to complete verification.',
      }
    }
    return {
      variant: 'cancelled',
      title: 'Run cancelled',
      description: 'This remediation run was cancelled; verification may be partial.',
      nextAction: null,
    }
  }

  if (st === 'completed') {
    if (verifyRuns === 0 && applyRuns > 0) {
      return {
        variant: 'warning',
        title: 'Verification not recorded on this session',
        description:
          'This run is completed, but verification is not recorded in step metrics. Check Run activity or run verification again if needed.',
        nextAction: 'If you expected a post-apply scan, use Re-scan and verify below when available.',
      }
    }
    if (vOk === true) {
      return {
        variant: 'verified',
        title: 'Post-apply verification passed',
        description: 'Post-apply verification completed successfully for this run.',
        nextAction: 'Review resolved findings and the project score on Docs health.',
      }
    }
    if (vOk === false) {
      return {
        variant: 'warning',
        title: 'Post-apply verification reported issues',
        description: 'Verification completed with issues reported for this run.',
        nextAction: 'Review new and reopened findings below, then address remaining items.',
      }
    }
    return {
      variant: 'info',
      title: 'Run completed',
      description: 'This run completed without detailed verification flags on the session record.',
      nextAction: 'Use the score and finding deltas below to confirm outcomes.',
    }
  }

  if (verifyRuns === 0) {
    return {
      variant: 'warning',
      title: 'Verification pending',
      description: 'Changes were applied; Re-scan and verify has not completed yet.',
      nextAction: 'Run Re-scan and verify when the workflow allows, or wait for the pipeline to finish.',
    }
  }

  if (st === 'running' || st === 'paused') {
    return {
      variant: 'info',
      title: 'Verification in progress',
      description: 'Re-scan or verification is still in progress.',
      nextAction: 'Watch Run activity for completion.',
    }
  }

  if (st === 'awaiting_input' || st === 'awaiting_approval') {
    return {
      variant: 'awaiting_input',
      title: 'Verification paused',
      description: 'The run is waiting for input or approval before verification can finish.',
      nextAction: 'Respond in the decision panel so the run can continue toward verification.',
    }
  }

  return {
    variant: 'info',
    title: 'Verification',
    description: 'See metrics and Run activity below.',
    nextAction: null,
  }
}
