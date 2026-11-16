import type { ReactNode } from 'react'
import { useMemo } from 'react'
import type { DocsHealthProjectPayload, DocsHealthSessionPayload } from '../../api/docsHealth'
import {
  ForgeEventTimeline,
  ForgeKeyValueGrid,
  ForgeStatusBanner,
  type ForgeKeyValueItem,
  type ForgeTimelineEvent,
} from '../../forgesdlc-kitchensink'
import { aggregateStepMetrics } from '../../lib/docsHealthStageFlow'
import {
  deriveVerificationBanner,
  extractNumericScore,
  mergeFindingDiff,
  scoreObject,
} from '../../lib/docsHealthVerification'

export type DocsHealthVerificationTabProps = {
  project: DocsHealthProjectPayload | null
  session: DocsHealthSessionPayload | null
  busy: string | null
  onStep: (step: string) => void
}

const LIST_CAP = 24

function fmtId(id: string) {
  const s = id.trim()
  if (s.length <= 36) return s
  return `${s.slice(0, 18)}…${s.slice(-8)}`
}

function FindingList({
  title,
  ids,
  emptyLabel,
}: {
  title: string
  ids: string[]
  emptyLabel: string
}) {
  const n = ids.length
  return (
    <div className="le-dh-verify__find-block">
      <h4 className="le-dh-wf-panel__h4">
        {title}{' '}
        <span className="le-dh-verify__count" aria-label={`Count: ${n}`}>
          ({n})
        </span>
      </h4>
      {n === 0 ? (
        <p className="le-dh-verify__find-empty forge-support">{emptyLabel}</p>
      ) : (
        <ul className="le-dh-verify__find-list">
          {ids.slice(0, LIST_CAP).map((id) => (
            <li key={id}>
              <code className="le-dh-verify__find-id" title={id}>
                {fmtId(id)}
              </code>
            </li>
          ))}
          {n > LIST_CAP ? (
            <li className="le-dh-verify__find-more forge-support">+{n - LIST_CAP} more (see full scan on project Docs health)</li>
          ) : null}
        </ul>
      )}
    </div>
  )
}

function sessionScoreDeltaLabel(
  session: DocsHealthSessionPayload | null,
  applyRuns: number,
  verifyRuns: number,
): { text: string; hint?: string } {
  if (!session) return { text: 'Not recorded', hint: 'No session payload.' }
  if (applyRuns === 0) return { text: 'Not applicable', hint: 'No apply step recorded; session delta is only meaningful after apply and verify.' }
  const st = String(session.status || '').toLowerCase()
  const hs = session.header_stats
  const delta = hs?.score_delta
  if ((st === 'running' || st === 'paused' || st === 'awaiting_input' || st === 'awaiting_approval') && verifyRuns === 0) {
    return { text: 'Pending', hint: 'Score delta is recorded when verification completes.' }
  }
  if (delta == null || Number.isNaN(Number(delta))) {
    if (st === 'completed' || verifyRuns > 0) {
      return { text: 'Not recorded', hint: 'Server did not return a session score delta for this run.' }
    }
    return { text: 'Pending', hint: 'Waiting for verification to finish.' }
  }
  const n = Number(delta)
  return { text: `${n > 0 ? '+' : ''}${n}`, hint: 'Session delta (post-verify vs baseline), when provided.' }
}

/**
 * Verify workflow panel: remediation verification status, scores, finding diffs, checks, and re-scan control.
 */
export function DocsHealthVerificationTab({ project, session, busy, onStep }: DocsHealthVerificationTabProps) {
  const banner = useMemo(() => deriveVerificationBanner(session), [session])
  const agg = useMemo(() => aggregateStepMetrics(session?.step_metrics), [session?.step_metrics])
  const applyRuns = agg.apply?.runs ?? 0
  const verifyRuns = agg.verify?.runs ?? 0

  const merged = useMemo(() => mergeFindingDiff(session, project), [session, project])
  const rc = project?.run_compare
  const lr = project?.latest_run as Record<string, unknown> | null | undefined
  const latestScoreRaw = lr?.score
  const latestNum = extractNumericScore(latestScoreRaw)
  const scoreMeta = scoreObject(latestScoreRaw)
  const hs = session?.header_stats
  const completion = session?.completion_summary
  const baseline =
    hs?.baseline_score != null && !Number.isNaN(Number(hs.baseline_score))
      ? Number(hs.baseline_score)
      : session?.baseline_score != null && !Number.isNaN(Number(session.baseline_score))
        ? Number(session.baseline_score)
        : null

  const sessionDelta = sessionScoreDeltaLabel(session, applyRuns, verifyRuns)

  const compareDeltaText =
    rc?.score_delta == null || Number.isNaN(Number(rc.score_delta))
      ? { text: 'Not available', hint: 'No prior run comparison in the current project snapshot.' as string | undefined }
      : { text: `${Number(rc.score_delta) > 0 ? '+' : ''}${rc.score_delta}`, hint: 'From project run_compare (vs prior scan).' }

  const pipelineOk = completion?.verification_pipeline_ok
  const pipelineLabel =
    pipelineOk === true
      ? 'Passed'
      : pipelineOk === false
        ? 'Issues reported'
        : applyRuns === 0
          ? 'Not applicable'
          : verifyRuns === 0
            ? 'Pending'
            : 'Not summarized'

  const postApplyItems: ForgeKeyValueItem[] = [
    {
      label: 'Verification pipeline (session completion)',
      value: pipelineLabel,
      title: 'completion_summary.verification_pipeline_ok',
    },
    {
      label: 'Verification scan id',
      value:
        completion?.verification_run_id || session?.verification_run_id ? (
          <code className="le-dh-run-id" title={String(completion?.verification_run_id || session?.verification_run_id)}>
            {String(completion?.verification_run_id || session?.verification_run_id).slice(0, 20)}
            …
          </code>
        ) : verifyRuns > 0 ? (
          'Not recorded on session'
        ) : (
          'Not run'
        ),
    },
    {
      label: 'Header verification check',
      value: hs?.verification
        ? hs.verification.ok === false
          ? 'Failed'
          : hs.verification.ok === true
            ? 'Passed'
            : 'Recorded'
        : verifyRuns > 0
          ? 'Not recorded in header'
          : 'Not run',
      title: hs?.verification?.detail,
    },
    {
      label: 'Header verification pipeline',
      value: hs?.verification_pipeline
        ? hs.verification_pipeline.ok === false
          ? 'Issues reported'
          : hs.verification_pipeline.ok === true
            ? 'Passed'
            : 'Recorded'
        : verifyRuns > 0
          ? 'Not recorded in header'
          : 'Not run',
      title: typeof hs?.verification_pipeline?.detail === 'string' ? hs.verification_pipeline.detail : undefined,
    },
  ]

  const timelineEvents: ForgeTimelineEvent[] = useMemo(() => {
    const rows = session?.events ?? []
    const filtered = rows.filter((e) => {
      const t = String(e.type || '').toLowerCase()
      const title = String(e.title || '').toLowerCase()
      const op = String(e.operation || '').toLowerCase()
      return (
        t.includes('verify') ||
        t.includes('verification') ||
        t.includes('scan') ||
        title.includes('verify') ||
        title.includes('verification') ||
        title.includes('re-scan') ||
        op.includes('verify')
      )
    })
    return filtered.slice(-12).map((e, i) => ({
      id: `${e.ts || 'ev'}-${i}-${e.type || ''}`,
      ts: e.ts,
      state:
        e.ok === true ? 'ok' : e.ok === false ? 'issue' : e.status ? String(e.status) : verifyRuns > 0 ? 'event' : undefined,
      summary: (e.title || e.type || 'Verification-related event') as ReactNode,
      details: (e.body || e.detail || e.stdout_summary || e.summary || e.raw_output) as ReactNode | undefined,
    }))
  }, [session?.events, verifyRuns])

  const verifyBusy = Boolean(busy)
  const canRunVerify = applyRuns > 0 && !verifyBusy
  const runCompareFindingDelta =
    rc?.finding_count_delta == null || Number.isNaN(Number(rc.finding_count_delta))
      ? 'Not available'
      : String(rc.finding_count_delta)

  return (
    <div className="le-dh-verify">
      <ForgeStatusBanner variant={banner.variant} title={banner.title} description={banner.description} role="status" />
      {banner.nextAction ? (
        <p className="le-dh-verify__next forge-support" role="note">
          <strong>Next:</strong> {banner.nextAction}
        </p>
      ) : null}

      <h4 className="le-dh-wf-panel__h4">Scores and deltas</h4>
      <div className="le-dh-verify__stat-grid" aria-label="Verification score metrics">
        <div className="le-dh-verify__stat">
          <div className="le-dh-verify__stat-label">Baseline score (session)</div>
          <div className="le-dh-verify__stat-value">{baseline == null ? 'Not recorded' : String(baseline)}</div>
          {baseline != null ? <div className="le-dh-verify__stat-hint forge-support">From header_stats / session baseline</div> : null}
        </div>
        <div className="le-dh-verify__stat">
          <div className="le-dh-verify__stat-label">Session score delta</div>
          <div className="le-dh-verify__stat-value">{sessionDelta.text}</div>
          {sessionDelta.hint ? <div className="le-dh-verify__stat-hint forge-support">{sessionDelta.hint}</div> : null}
        </div>
        <div className="le-dh-verify__stat">
          <div className="le-dh-verify__stat-label">Score delta vs prior project scan</div>
          <div className="le-dh-verify__stat-value">{compareDeltaText.text}</div>
          {compareDeltaText.hint ? <div className="le-dh-verify__stat-hint forge-support">{compareDeltaText.hint}</div> : null}
        </div>
        <div className="le-dh-verify__stat">
          <div className="le-dh-verify__stat-label">Finding count delta (project)</div>
          <div className="le-dh-verify__stat-value">{runCompareFindingDelta}</div>
          <div className="le-dh-verify__stat-hint forge-support">From run_compare vs prior scan</div>
        </div>
        <div className="le-dh-verify__stat">
          <div className="le-dh-verify__stat-label">Latest project scan score</div>
          <div className="le-dh-verify__stat-value">{latestNum == null ? 'Not available' : String(latestNum)}</div>
          {lr?.id ? (
            <div className="le-dh-verify__stat-hint forge-support">
              Scan id <code className="le-dh-run-id">{String(lr.id).slice(0, 14)}…</code>
            </div>
          ) : (
            <div className="le-dh-verify__stat-hint forge-support">From project latest_run snapshot</div>
          )}
        </div>
        <div className="le-dh-verify__stat">
          <div className="le-dh-verify__stat-label">Potential delta if resolved</div>
          <div className="le-dh-verify__stat-value">
            {scoreMeta?.potential_delta_if_resolved == null || Number.isNaN(Number(scoreMeta.potential_delta_if_resolved))
              ? 'Not available'
              : String(scoreMeta.potential_delta_if_resolved)}
          </div>
          <div className="le-dh-verify__stat-hint forge-support">From latest scan score model (when provided)</div>
        </div>
      </div>

      {scoreMeta?.formula ? (
        <p className="le-dh-verify__formula forge-support">
          <strong>Score formula (latest scan):</strong> <code>{scoreMeta.formula}</code>
        </p>
      ) : null}

      <div className="le-dh-verify__find-grid">
        <FindingList
          title="Resolved findings"
          ids={merged.resolved}
          emptyLabel={
            verifyRuns === 0 && applyRuns > 0
              ? 'None recorded yet — verification still pending or diff not returned.'
              : 'None recorded for this comparison window.'
          }
        />
        <FindingList
          title="New findings"
          ids={merged.newFindings}
          emptyLabel={verifyRuns === 0 && applyRuns > 0 ? 'None yet — pending verification diff.' : 'None recorded.'}
        />
        <FindingList
          title="Reopened findings"
          ids={merged.reopened}
          emptyLabel={verifyRuns === 0 && applyRuns > 0 ? 'None yet — pending verification diff.' : 'None recorded.'}
        />
      </div>

      <h4 className="le-dh-wf-panel__h4">Post-apply checks</h4>
      <ForgeKeyValueGrid items={postApplyItems} aria-label="Post-apply verification checks" />

      <h4 className="le-dh-wf-panel__h4">Verification activity</h4>
      <ForgeEventTimeline
        events={timelineEvents}
        emptyLabel="No verification-tagged events in this session log yet."
        className="le-dh-verify__timeline"
      />

      <div className="le-dh-verify__controls">
        <button
          type="button"
          className="le-btn le-btn--primary"
          disabled={!canRunVerify}
          onClick={() => onStep('verify')}
        >
          {verifyBusy ? 'Pipeline busy…' : 'Re-scan and verify'}
        </button>
        {!canRunVerify && applyRuns === 0 ? (
          <span className="le-dh-verify__control-hint forge-support">Apply changes first — verify runs after apply.</span>
        ) : !canRunVerify && verifyBusy ? (
          <span className="le-dh-verify__control-hint forge-support">Wait for the current step to finish, then retry.</span>
        ) : null}
      </div>
    </div>
  )
}
