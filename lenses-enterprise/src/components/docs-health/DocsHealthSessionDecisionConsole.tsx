import { Link } from 'react-router-dom'
import { TechnicalDetails } from '../page'
import type { DocsHealthSessionPayload } from '../../api/docsHealth'
import {
  deriveRemediationViewState,
  hasAppliedAwaitingVerify,
  hasReviewableChange,
  inferRetryStep,
  likelyNoAppliedChangesOnCancel,
  type RemediationViewState,
} from '../../lib/docsHealthSessionViewState'

export type DocsHealthSessionDecisionConsoleProps = {
  encProject: string
  session: DocsHealthSessionPayload | null
  busy: string | null
  cancelBusy: boolean
  replyText: string
  replyBusy: boolean
  resumeBusy: boolean
  onCancelSession?: () => void
  onSendReply: (opts: { reply_text?: string; choice_id?: string; confirm?: boolean }) => void | Promise<void>
  onResume: () => void | Promise<void>
  onStep: (step: string) => void | Promise<void>
  /** Opens the Draft changes workflow stage and draft artifact surface (e.g. before scroll to anchor). */
  onNavigateToDraft?: () => void
}

function scrollToId(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

/** Destructive / overflow actions — keeps cancel out of the primary scanning path. */
function RemediationOverflowMenu({
  cancelBusy,
  onCancelSession,
}: {
  cancelBusy: boolean
  onCancelSession: () => void
}) {
  return (
    <details className="le-dh-more-actions">
      <summary className="le-dh-more-actions__summary le-btn le-btn--ghost le-btn--small" aria-label="More actions">
        More
      </summary>
      <div className="le-dh-more-actions__panel">
        <button
          type="button"
          className="le-btn le-btn--small le-dh-more-actions__danger"
          disabled={cancelBusy}
          data-testid="docs-health-cancel-run"
          aria-label="Cancel documentation remediation run"
          onClick={(ev) => {
            ;(ev.currentTarget.closest('details') as HTMLDetailsElement | null)?.removeAttribute('open')
            void onCancelSession()
          }}
        >
          {cancelBusy ? 'Cancelling…' : 'Cancel run'}
        </button>
      </div>
    </details>
  )
}

/** Primary + secondary actions for the remediation run (used inside the compact summary CTA row). */
export function RemediationPrimaryActions({
  view,
  encProject,
  session,
  blocked,
  busy,
  cancelBusy,
  replyText,
  replyBusy,
  resumeBusy,
  hasReviewable,
  branchHint,
  appliedAwait,
  allowNewSteps,
  onCancelSession,
  onSendReply,
  onResume,
  onStep,
  onNavigateToDraft,
}: {
  view: RemediationViewState
  encProject: string
  session: DocsHealthSessionPayload | null
  blocked: boolean
  busy: string | null
  cancelBusy: boolean
  replyText: string
  replyBusy: boolean
  resumeBusy: boolean
  hasReviewable: boolean
  branchHint?: string
  appliedAwait: boolean
  allowNewSteps: boolean
  onCancelSession?: () => void
  onSendReply: DocsHealthSessionDecisionConsoleProps['onSendReply']
  onResume: DocsHealthSessionDecisionConsoleProps['onResume']
  onStep: DocsHealthSessionDecisionConsoleProps['onStep']
  onNavigateToDraft?: DocsHealthSessionDecisionConsoleProps['onNavigateToDraft']
}) {
  if (view === 'loading') {
    return <span className="le-muted forge-support">Loading run…</span>
  }

  if (view === 'cancelled') {
    return (
      <>
        <button
          type="button"
          className="le-btn le-btn--primary"
          disabled={resumeBusy}
          onClick={() => void onResume()}
        >
          {resumeBusy ? 'Resuming…' : 'Resume run'}
        </button>
        <Link className="le-btn" to={`/projects/${encProject}/docs-health`}>
          Start new run
        </Link>
      </>
    )
  }

  if (view === 'failed') {
    const retry = inferRetryStep(session)
    return (
      <>
        <button type="button" className="le-btn le-btn--primary" disabled={blocked} onClick={() => void onStep(retry)}>
          {blocked ? 'Working…' : 'Retry failed stage'}
        </button>
        <button
          type="button"
          className="le-btn le-btn--ghost"
          title="Scroll only — does not start a step or call the server."
          onClick={() => scrollToId('dh-activity-log')}
        >
          Open Run activity
        </button>
      </>
    )
  }

  if (view === 'verified') {
    return (
      <Link className="le-btn le-btn--primary" to={`/projects/${encProject}/docs-health`}>
        View results
      </Link>
    )
  }

  if (view === 'applied_await_verify' || appliedAwait) {
    return (
      <button
        type="button"
        className="le-btn le-btn--primary"
        disabled={blocked || !allowNewSteps}
        onClick={() => void onStep('verify')}
      >
        {blocked ? 'Working…' : 'Re-scan and verify'}
      </button>
    )
  }

  if (view === 'awaiting_input') {
    const canContinue = Boolean(replyText.trim())
    return (
      <>
        <button type="button" className="le-btn le-btn--primary" onClick={() => scrollToId('docs-health-reply-panel')}>
          Answer question
        </button>
        <button
          type="button"
          className="le-btn"
          disabled={replyBusy}
          title={!canContinue ? 'Add a reply below, or pick a choice, then continue.' : undefined}
          onClick={() =>
            void (async () => {
              if (canContinue) await onSendReply({ reply_text: replyText })
              else scrollToId('docs-health-reply-panel')
            })()
          }
        >
          {replyBusy ? 'Sending…' : 'Continue'}
        </button>
      </>
    )
  }

  if (view === 'awaiting_approval') {
    const approveLabel = branchHint ? 'Approve and apply to branch' : 'Approve for apply'
    return (
      <>
        <button
          type="button"
          className={hasReviewable ? 'le-btn' : 'le-btn le-btn--primary'}
          onClick={() => {
            if (onNavigateToDraft) onNavigateToDraft()
            else scrollToId('docs-health-drafts-anchor')
          }}
        >
          Open Changes
        </button>
        {hasReviewable ? (
          <button
            type="button"
            className="le-btn le-btn--primary"
            disabled={replyBusy || blocked}
            onClick={() =>
              void (async () => {
                await onSendReply({ confirm: true })
                if (allowNewSteps) await onStep('apply')
              })()
            }
          >
            {replyBusy ? 'Sending…' : approveLabel}
          </button>
        ) : null}
        <button type="button" className="le-btn" disabled={replyBusy || blocked} onClick={() => void onSendReply({ confirm: false })}>
          Reject
        </button>
      </>
    )
  }

  if (view === 'running') {
    const noStepsYet = !(session?.step_metrics && session.step_metrics.length > 0)
    return (
      <>
        {noStepsYet ? (
          <>
            <button
              type="button"
              className="le-btn le-btn--primary"
              disabled={blocked || !allowNewSteps}
              title="First LLM step: executive cluster summary"
              onClick={() => void onStep('cluster_brief')}
            >
              {busy === 'cluster_brief' ? 'Cluster brief…' : 'Start · Cluster brief'}
            </button>
            <button
              type="button"
              className="le-btn"
              disabled={blocked || !allowNewSteps}
              title="LLM context pass over findings (can follow a cluster brief)"
              onClick={() => void onStep('enrich')}
            >
              {busy === 'enrich' ? 'Enrich…' : 'Start · Gather context'}
            </button>
          </>
        ) : null}
        <button
          type="button"
          className={noStepsYet ? 'le-btn' : 'le-btn le-btn--primary'}
          title="Scroll only — does not start a step or call the server."
          onClick={() => scrollToId('dh-activity-log')}
        >
          Open Run activity
        </button>
        {onCancelSession ? (
          <RemediationOverflowMenu cancelBusy={cancelBusy} onCancelSession={onCancelSession} />
        ) : (
          <span className="le-muted forge-support">Cancel is not available for this run.</span>
        )}
      </>
    )
  }

  return null
}

export function RemediationAdvancedPipelineSteps({
  allowNewSteps,
  showApply,
  blocked,
  busy,
  onStep,
}: {
  allowNewSteps: boolean
  showApply: boolean
  blocked: boolean
  busy: string | null
  onStep: DocsHealthSessionDecisionConsoleProps['onStep']
}) {
  const dis = !allowNewSteps || blocked
  return (
    <TechnicalDetails summary="Advanced pipeline steps" defaultOpen={false}>
      <p className="forge-support" style={{ marginTop: 0 }}>
        Individual stages for power users. After cancel, new stages cannot start (an in-flight request may still finish).
      </p>
      <div className="le-dh-advanced-steps">
        <button type="button" className="le-btn le-btn--small" disabled={dis} onClick={() => void onStep('cluster_brief')}>
          {busy === 'cluster_brief' ? '…' : 'Cluster'}
        </button>
        <button type="button" className="le-btn le-btn--small" disabled={dis} onClick={() => void onStep('enrich')}>
          {busy === 'enrich' ? '…' : 'Enrich'}
        </button>
        <button type="button" className="le-btn le-btn--small" disabled={dis} onClick={() => void onStep('draft')}>
          {busy === 'draft' ? '…' : 'Writer'}
        </button>
        <button type="button" className="le-btn le-btn--small" disabled={dis} onClick={() => void onStep('diagram_draft')}>
          {busy === 'diagram_draft' ? '…' : 'Diagram'}
        </button>
        <button type="button" className="le-btn le-btn--small" disabled={dis} onClick={() => void onStep('decision_stub')}>
          {busy === 'decision_stub' ? '…' : 'ADR'}
        </button>
        <button type="button" className="le-btn le-btn--small" disabled={dis} onClick={() => void onStep('review')}>
          {busy === 'review' ? '…' : 'Review'}
        </button>
        {showApply ? (
          <button type="button" className="le-btn le-btn--small" disabled={dis} onClick={() => void onStep('apply')}>
            {busy === 'apply' ? '…' : 'Apply'}
          </button>
        ) : (
          <span className="le-muted le-btn le-btn--small le-btn--ghost" style={{ cursor: 'not-allowed' }} title="Not available">
            Apply
          </span>
        )}
        <button type="button" className="le-btn le-btn--small" disabled={dis} onClick={() => void onStep('verify')}>
          {busy === 'verify' ? '…' : 'Verify'}
        </button>
      </div>
    </TechnicalDetails>
  )
}

/** Shared view-state helpers for the session page shell (plain function — safe outside React components). */
export function getRemediationConsoleContext(session: DocsHealthSessionPayload | null, busy: string | null) {
  const view = deriveRemediationViewState(session)
  const hasReviewable = hasReviewableChange(session)
  const cancelledNoApply = likelyNoAppliedChangesOnCancel(session)
  const blocked = busy !== null
  const allowNewSteps = view !== 'cancelled'
  const showApplyInAdvanced = allowNewSteps && hasReviewable
  const branchHint = session?.suggested_git_branch
  const appliedAwait = session ? hasAppliedAwaitingVerify(session) : false
  return {
    view,
    hasReviewable,
    cancelledNoApply,
    blocked,
    allowNewSteps,
    showApplyInAdvanced,
    branchHint,
    appliedAwait,
  }
}
