import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import type { DocsHealthSessionPayload } from '../../api/docsHealth'
import { ForgeDecisionActionBar, ForgeStatusBanner } from '../../forgesdlc-kitchensink'
import { getRemediationBannerMessage } from '../../lib/docsHealthSessionViewState'
import {
  getRemediationConsoleContext,
  RemediationPrimaryActions,
} from './DocsHealthSessionDecisionConsole'

function sess(p: Partial<DocsHealthSessionPayload>): DocsHealthSessionPayload {
  return p as DocsHealthSessionPayload
}

const handlers = {
  onSendReply: vi.fn(),
  onResume: vi.fn(),
  onStep: vi.fn(),
  onCancelSession: vi.fn(),
}

beforeEach(() => {
  handlers.onSendReply.mockClear()
  handlers.onResume.mockClear()
  handlers.onStep.mockClear()
  handlers.onCancelSession.mockClear()
})

function renderPrimaryStrip(session: DocsHealthSessionPayload | null, busy: string | null = null) {
  const ctx = getRemediationConsoleContext(session, busy)
  return render(
    <MemoryRouter>
      <ForgeDecisionActionBar sticky={false} aria-label="Primary run actions">
        <RemediationPrimaryActions
          view={ctx.view}
          encProject="e2e_proj"
          session={session}
          blocked={ctx.blocked}
          busy={busy}
          cancelBusy={false}
          replyText=""
          replyBusy={false}
          resumeBusy={false}
          hasReviewable={ctx.hasReviewable}
          branchHint={ctx.branchHint}
          appliedAwait={ctx.appliedAwait}
          allowNewSteps={ctx.allowNewSteps}
          onCancelSession={handlers.onCancelSession}
          onSendReply={handlers.onSendReply}
          onResume={handlers.onResume}
          onStep={handlers.onStep}
        />
      </ForgeDecisionActionBar>
    </MemoryRouter>,
  )
}

function renderBanner(session: DocsHealthSessionPayload | null, busy: string | null = null) {
  const ctx = getRemediationConsoleContext(session, busy)
  const banner = getRemediationBannerMessage(ctx.view, session, {
    hasReviewable: ctx.hasReviewable,
    cancelledNoApplyChanges: ctx.cancelledNoApply,
  })
  if (!banner) throw new Error('expected banner for this scenario')
  return render(
    <ForgeStatusBanner
      variant={banner.variant}
      title={banner.title}
      description={banner.description}
      role="status"
    />,
  )
}

describe('RemediationPrimaryActions (session decision CTAs)', () => {
  it('running with steps: Open Run activity is primary; cancel is under More', () => {
    renderPrimaryStrip(sess({ status: 'running', id: 's', step_metrics: [{ step: 'enrich' }] }), null)
    const live = screen.getByRole('button', { name: /Open Run activity/i })
    expect(live.className).toMatch(/le-btn--primary/)
    const more = document.querySelector('.le-dh-more-actions summary') as HTMLElement | null
    expect(more).toBeTruthy()
    fireEvent.click(more!)
    fireEvent.click(screen.getByTestId('docs-health-cancel-run'))
    expect(handlers.onCancelSession).toHaveBeenCalledTimes(1)
  })

  it('cancelled: resume and start new run', () => {
    renderPrimaryStrip(sess({ status: 'cancelled', id: 's1' }))
    expect(screen.getByRole('button', { name: /Resume run/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Start new run/i })).toBeInTheDocument()
  })

  it('awaiting_approval with reviewable change: approve and reject', () => {
    renderPrimaryStrip(
      sess({
        status: 'awaiting_approval',
        id: 's2',
        proposed_patch: { path: 'README.md', content: 'hello' },
        suggested_git_branch: 'docs/fix',
      }),
    )
    expect(screen.getByRole('button', { name: /Open Changes/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Approve and apply to branch/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^Reject$/i })).toBeInTheDocument()
  })

  it('applied_await_verify: Re-scan and verify primary', () => {
    renderPrimaryStrip(
      sess({
        status: 'running',
        id: 's3',
        step_metrics: [{ step: 'apply' }],
      }),
    )
    expect(screen.getByRole('button', { name: /Re-scan and verify/i })).toBeInTheDocument()
  })

  it('verified (completed): link to project docs health results', () => {
    renderPrimaryStrip(
      sess({ status: 'completed', id: 's4', completion_summary: { verification_pipeline_ok: true } }),
    )
    const link = screen.getByRole('link', { name: /View results/i })
    expect(link).toBeInTheDocument()
    expect(link.getAttribute('href')).toContain('/docs-health')
  })
})

describe('Remediation banner copy (ForgeStatusBanner)', () => {
  it('shows cancelled banner title', () => {
    renderBanner(sess({ status: 'cancelled', id: 'x', step_metrics: [], header_stats: { files_changed: 0 } }))
    expect(screen.getByText(/Run cancelled/i)).toBeInTheDocument()
  })

  it('shows awaiting approval banner when reviewable', () => {
    renderBanner(
      sess({
        status: 'awaiting_approval',
        id: 'y',
        proposed_patch: { path: 'a.md', content: 'b' },
      }),
    )
    expect(screen.getByText(/Review before apply/i)).toBeInTheDocument()
  })
})
