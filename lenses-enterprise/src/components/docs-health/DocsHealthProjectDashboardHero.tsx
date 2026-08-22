import { Link } from 'react-router-dom'
import type { DocsHealthProjectPayload, DocsHealthScore } from '../../api/docsHealth'
import { STUDIO_VOCAB } from '../../nav/studioVisibleCopy'
import './docs-health-project-page.css'

type LatestRunLite = {
  id?: string
  finding_count?: number
  finding_diff?: {
    resolved_from_prior_scan?: string[]
    new_since_prior_scan?: string[]
    reopened_findings?: string[]
  }
}

type Props = {
  encProject: string
  score: DocsHealthScore | undefined
  hasRun: boolean
  allClear: boolean
  latest: LatestRunLite | null | undefined
  data: DocsHealthProjectPayload
  scanning: boolean
  refreshing: boolean
  indexing: boolean
  scanInlineMessage: { tone: 'ok' | 'err'; text: string } | null
  onRunScan: () => void
  onRunInventory: () => void
}

export function DocsHealthProjectDashboardHero({
  encProject,
  score,
  hasRun,
  allClear,
  latest,
  data,
  scanning,
  refreshing,
  indexing,
  scanInlineMessage,
  onRunScan,
  onRunInventory,
}: Props) {
  const fd = latest?.finding_diff
  const diffBits: string[] = []
  if (fd?.resolved_from_prior_scan?.length) diffBits.push(`resolved ${fd.resolved_from_prior_scan.length}`)
  if (fd?.new_since_prior_scan?.length) diffBits.push(`new ${fd.new_since_prior_scan.length}`)
  if (fd?.reopened_findings?.length) diffBits.push(`reopened ${fd.reopened_findings.length}`)

  return (
    <div className="le-dh-hero">
      <div>
        {!hasRun ? (
          <p className="le-muted forge-support" role="status" style={{ marginTop: 0 }}>
            No scan yet. Run a deterministic scan to compute the score and follow-up work items.
          </p>
        ) : allClear ? (
          <p className="forge-support" role="status" style={{ marginTop: 0, color: 'var(--le-ok-text, inherit)' }}>
            All checks passed — no findings. Re-run after substantive doc edits to confirm the score stays green.
          </p>
        ) : null}

        <div aria-live="polite" aria-busy={scanning || refreshing}>
          {(scanning || refreshing) && (
            <p className="forge-support" role="status" style={{ marginBottom: '0.35rem' }}>
              {scanning ? 'Running deterministic scan on the repository…' : 'Refreshing score and findings…'}
            </p>
          )}
          <div className="le-dh-hero__scoreline">
            <p className="le-dh-hero__score">
              {score?.value != null ? `${score.value}` : '—'}
              <span className="le-muted" style={{ fontSize: '1rem', fontWeight: 400 }}>
                /100
              </span>
            </p>
            <p className="le-dh-hero__meta forge-support">
              Findings: <strong>{latest?.finding_count ?? '—'}</strong>
              {latest?.id ? (
                <>
                  {' '}
                  · run <code>{latest.id.slice(0, 12)}…</code>
                </>
              ) : null}
            </p>
          </div>

          {score?.potential_delta_if_resolved != null && score.potential_delta_if_resolved > 0 ? (
            <p className="forge-support le-dh-hero__meta" style={{ margin: '0.25rem 0 0' }}>
              Up to <strong>+{score.potential_delta_if_resolved}</strong> pts if all open findings cleared (cap 100).
              Recovery pts: <strong>{score.total_expected_recovery_points ?? '—'}</strong>.
            </p>
          ) : null}

          {data.run_compare?.score_delta != null ? (
            <p className="forge-support le-dh-hero__meta" style={{ margin: '0.35rem 0 0' }}>
              vs prior run: score{' '}
              <strong>
                {data.run_compare.score_delta >= 0 ? '+' : ''}
                {data.run_compare.score_delta}
              </strong>
              , findings{' '}
              <strong>
                {data.run_compare.finding_count_delta != null && data.run_compare.finding_count_delta >= 0 ? '+' : ''}
                {data.run_compare.finding_count_delta ?? '—'}
              </strong>
              .
            </p>
          ) : null}

          {diffBits.length ? (
            <p className="le-muted le-dh-hero__meta" style={{ margin: '0.25rem 0 0' }}>
              Finding churn: {diffBits.join(' · ')}
            </p>
          ) : null}
        </div>

        {scanInlineMessage ? (
          <p
            className="forge-support"
            role={scanInlineMessage.tone === 'err' ? 'alert' : 'status'}
            style={{
              marginTop: '0.45rem',
              whiteSpace: scanInlineMessage.tone === 'err' ? 'pre-line' : 'normal',
              color:
                scanInlineMessage.tone === 'ok'
                  ? 'var(--le-ok-text, inherit)'
                  : 'var(--le-danger-text, #f87171)',
            }}
          >
            {scanInlineMessage.text}
          </p>
        ) : null}
      </div>

      <div className="le-dh-hero__actions">
        <button type="button" className="le-btn le-btn--primary" disabled={scanning} aria-busy={scanning} onClick={onRunScan}>
          {scanning ? 'Scanning…' : 'Run markdown scan'}
        </button>
        <button type="button" className="le-btn" disabled={indexing} onClick={onRunInventory}>
          {indexing ? 'Refreshing…' : 'Refresh doc list'}
        </button>
        {refreshing && !scanning ? <span className="le-muted forge-support">Updating…</span> : null}
        <Link className="le-btn le-btn--small" to={`/projects/${encProject}/docs-health/master`}>
          {STUDIO_VOCAB.docsHealthMaster}
        </Link>
      </div>
    </div>
  )
}
