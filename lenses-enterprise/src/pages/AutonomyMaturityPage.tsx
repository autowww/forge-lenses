import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError } from '../api/http'
import {
  fetchAutonomyMaturityOverview,
  type AutonomyMaturityOverview,
} from '../api/autonomyMaturity'
import { PageHeader, StatePanel } from '../components/page'
import { resolveUxFailure, type UxResolvedFailure } from '../lib/uxPageState'
import { ROUTE_SUBTITLE } from '../nav/studioVisibleCopy'

export function gradeBadge(level?: string, sublevel?: string | null, grade?: string): string {
  const core = sublevel || level || 'L0'
  return `${core}${grade ?? ''}`
}

export function AutonomyMaturityPage() {
  const [data, setData] = useState<AutonomyMaturityOverview | null>(null)
  const [err, setErr] = useState<UxResolvedFailure | null>(null)
  const [disabled, setDisabled] = useState(false)
  const [loading, setLoading] = useState(true)
  const [retryNonce, setRetryNonce] = useState(0)

  useEffect(() => {
    let cancel = false
    setLoading(true)
    fetchAutonomyMaturityOverview()
      .then((d) => {
        if (cancel) return
        setData(d)
        setErr(null)
      })
      .catch((e) => {
        if (cancel) return
        if (e instanceof ApiError && e.status === 404) {
          setDisabled(true)
          setErr(null)
        } else {
          setErr(resolveUxFailure(e))
        }
      })
      .finally(() => {
        if (!cancel) setLoading(false)
      })
    return () => {
      cancel = true
    }
  }, [retryNonce])

  return (
    <>
      <PageHeader title="Autonomy maturity" subtitle={ROUTE_SUBTITLE.autonomyMaturity} />
      <section className="le-card le-readiness-story" aria-label="readinessStory">
        <h2 className="le-cc-section__title">Ready to delegate?</h2>
        <p className="forge-support plainReadiness">
          This is a plain readiness narrative — not a grade to optimize. Each project shows what the workspace scan
          actually observed (gates, run evidence, repeatability) and the next safe step before you delegate more work to
          agents.
        </p>
      </section>
      {loading ? (
        <StatePanel
          variant="loading"
          title="Assessing workspace autonomy maturity"
          description="Reading deterministic repo signals — gates, run evidence, repeatability."
        />
      ) : null}
      {err ? (
        <StatePanel
          variant="error"
          title={err.title}
          description={err.description}
          technicalDetail={err.technical}
          actions={
            <button type="button" className="le-btn le-btn--primary" onClick={() => setRetryNonce((n) => n + 1)}>
              Retry
            </button>
          }
        />
      ) : null}
      {disabled ? (
        <StatePanel
          variant="empty"
          title="Autonomy maturity is disabled"
          description="Set LENSES_EXPERIMENTAL_AUTONOMY_MATURITY=1 on the Lenses server (and VITE_EXPERIMENTAL_AUTONOMY_MATURITY=1 for the Studio build) to enable this assessment."
        />
      ) : null}
      {!loading && !err && !disabled && data?.projects ? (
        data.projects.length === 0 ? (
          <StatePanel
            variant="empty"
            title="No git projects found"
            description="The scan found no workspace children to assess."
          />
        ) : (
          <>
            <p className="le-muted" style={{ fontSize: '0.85rem' }}>
              Observed from repo signals per the Blueprints autonomy maturity framework — weakest first.
              Wizard planning intent is never counted as evidence.
            </p>
            <table className="le-table" style={{ width: '100%', fontSize: '0.88rem' }}>
              <thead>
                <tr>
                  <th style={{ textAlign: 'left' }}>Project</th>
                  <th style={{ textAlign: 'left' }}>Observed</th>
                  <th style={{ textAlign: 'right' }}>Score</th>
                  <th style={{ textAlign: 'left' }}>Next step</th>
                </tr>
              </thead>
              <tbody>
                {data.projects.map((row) => (
                  <tr key={row.project}>
                    <td>
                      <Link to={`/projects/${encodeURIComponent(row.project ?? '')}/autonomy-maturity`}>
                        {row.project}
                      </Link>
                    </td>
                    <td>
                      <code className="le-mono">
                        {gradeBadge(row.observed_level, row.observed_sublevel, row.observed_grade)}
                      </code>
                    </td>
                    <td style={{ textAlign: 'right' }}>{row.score ?? 0}/100</td>
                    <td className="le-muted">{row.recommendations?.[0] ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )
      ) : null}
    </>
  )
}
