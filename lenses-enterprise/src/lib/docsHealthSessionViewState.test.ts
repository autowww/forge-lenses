import { describe, expect, it } from 'vitest'
import type { DocsHealthSessionPayload } from '../api/docsHealth'
import {
  deriveRemediationViewState,
  getRemediationBannerMessage,
  hasAppliedAwaitingVerify,
  hasReviewableChange,
  inferRetryStep,
  likelyNoAppliedChangesOnCancel,
} from './docsHealthSessionViewState'

function sess(p: Partial<DocsHealthSessionPayload>): DocsHealthSessionPayload {
  return p as DocsHealthSessionPayload
}

describe('deriveRemediationViewState', () => {
  it('returns loading when session is null', () => {
    expect(deriveRemediationViewState(null)).toBe('loading')
  })

  it('maps API statuses to view states', () => {
    expect(deriveRemediationViewState(sess({ status: 'cancelled' }))).toBe('cancelled')
    expect(deriveRemediationViewState(sess({ status: 'failed' }))).toBe('failed')
    expect(deriveRemediationViewState(sess({ status: 'awaiting_input' }))).toBe('awaiting_input')
    expect(deriveRemediationViewState(sess({ status: 'awaiting_approval' }))).toBe('awaiting_approval')
    expect(deriveRemediationViewState(sess({ status: 'completed' }))).toBe('verified')
  })

  it('returns applied_await_verify when apply ran but verify did not and run is still live', () => {
    const session = sess({
      status: 'running',
      step_metrics: [{ step: 'apply' }],
    })
    expect(deriveRemediationViewState(session)).toBe('applied_await_verify')
  })

  it('returns running when apply and verify both have runs', () => {
    const session = sess({
      status: 'running',
      step_metrics: [{ step: 'apply' }, { step: 'verify' }],
    })
    expect(deriveRemediationViewState(session)).toBe('running')
  })

  it('does not use applied_await_verify when status is terminal', () => {
    const session = sess({
      status: 'completed',
      step_metrics: [{ step: 'apply' }],
    })
    expect(deriveRemediationViewState(session)).toBe('verified')
  })
})

describe('hasAppliedAwaitingVerify', () => {
  it('is true only when apply has runs, verify does not, and status is live', () => {
    expect(
      hasAppliedAwaitingVerify(
        sess({ status: 'running', step_metrics: [{ step: 'apply' }, { step: 'draft' }] }),
      ),
    ).toBe(true)
    expect(hasAppliedAwaitingVerify(sess({ status: 'completed', step_metrics: [{ step: 'apply' }] }))).toBe(false)
  })
})

describe('likelyNoAppliedChangesOnCancel', () => {
  it('is true when no apply metrics and no files changed', () => {
    expect(likelyNoAppliedChangesOnCancel(sess({ step_metrics: [], header_stats: {} }))).toBe(true)
  })

  it('is false when apply has run', () => {
    expect(likelyNoAppliedChangesOnCancel(sess({ step_metrics: [{ step: 'apply' }] }))).toBe(false)
  })
})

describe('inferRetryStep', () => {
  it('returns last known backend step from step_metrics', () => {
    expect(
      inferRetryStep(
        sess({
          step_metrics: [{ step: 'draft' }, { step: 'review' }],
        }),
      ),
    ).toBe('review')
  })

  it('defaults to verify when no metrics', () => {
    expect(inferRetryStep(sess({}))).toBe('verify')
  })
})

describe('getRemediationBannerMessage', () => {
  const baseSession = sess({ id: 's1', status: 'running' })

  it('returns null for loading', () => {
    expect(
      getRemediationBannerMessage('loading', baseSession, {
        hasReviewable: false,
        cancelledNoApplyChanges: false,
      }),
    ).toBeNull()
  })

  it('cancelled: distinguishes no-apply vs had work', () => {
    const a = getRemediationBannerMessage('cancelled', baseSession, {
      hasReviewable: false,
      cancelledNoApplyChanges: true,
    })
    expect(a?.title).toBe('Run cancelled')
    expect(String(a?.description)).toContain('before changes were applied')

    const b = getRemediationBannerMessage('cancelled', baseSession, {
      hasReviewable: false,
      cancelledNoApplyChanges: false,
    })
    expect(String(b?.description)).toContain('The run was stopped')
  })

  it('awaiting_approval: reviewable vs not', () => {
    const noPatch = getRemediationBannerMessage('awaiting_approval', baseSession, {
      hasReviewable: false,
      cancelledNoApplyChanges: false,
    })
    expect(noPatch?.title).toBe('Waiting for review')

    const withPatch = getRemediationBannerMessage(
      'awaiting_approval',
      sess({ ...baseSession, proposed_patch: { path: 'a.md', content: 'x' } }),
      { hasReviewable: true, cancelledNoApplyChanges: false },
    )
    expect(withPatch?.title).toBe('Review before apply')
  })

  it('applied_await_verify warns to verify next', () => {
    const m = getRemediationBannerMessage('applied_await_verify', baseSession, {
      hasReviewable: false,
      cancelledNoApplyChanges: false,
    })
    expect(m?.variant).toBe('warning')
    expect(m?.title).toContain('verify')
  })

  it('verified reflects completion summary flag', () => {
    const ok = getRemediationBannerMessage(
      'verified',
      sess({ ...baseSession, status: 'completed', completion_summary: { verification_pipeline_ok: true } }),
      { hasReviewable: false, cancelledNoApplyChanges: false },
    )
    expect(String(ok?.description)).toContain('Verification finished')

    const bad = getRemediationBannerMessage(
      'verified',
      sess({ ...baseSession, status: 'completed', completion_summary: { verification_pipeline_ok: false } }),
      { hasReviewable: false, cancelledNoApplyChanges: false },
    )
    expect(String(bad?.description)).toContain('issues')
  })
})

describe('hasReviewableChange', () => {
  it('is true when proposed_patch has content', () => {
    expect(hasReviewableChange(sess({ proposed_patch: { path: 'a.md', content: 'hi' } }))).toBe(true)
  })

  it('is false when empty', () => {
    expect(hasReviewableChange(sess({}))).toBe(false)
  })
})
