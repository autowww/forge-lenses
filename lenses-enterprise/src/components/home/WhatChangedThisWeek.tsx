import { Link } from 'react-router-dom'
import type { CompareModeId, TimeHorizonId } from '../../context/ShellChromeContext'
import type { OverviewChartPayload } from '../../api/chartOverview'
import {
  horizonPeriodPhrase,
  horizonToWindowDays,
  sumCommitDailySevenDay,
  topReposByLinesAdded,
  whatChangedSectionTitle,
} from '../../api/chartOverview'
import { DeltaPill } from '../metrics'
import { StatePanel, TechnicalDetails } from '../page'
import { formatDelta, lookupPrevLinesAdded, tierToClass } from '../../lib/kpiTrendUi'
import { STUDIO_VOCAB } from '../../nav/studioVisibleCopy'

type Props = {
  chart: OverviewChartPayload | null
  chartError: boolean
  timeHorizon: TimeHorizonId
  compareMode: CompareModeId
  overviewDataLoading?: boolean
}

export function WhatChangedThisWeek({
  chart,
  chartError,
  timeHorizon,
  compareMode,
  overviewDataLoading = false,
}: Props) {
  const total = chart ? sumCommitDailySevenDay(chart) : null
  const top = chart ? topReposByLinesAdded(chart, 8) : []
  const ct = chart?.kpi_trends?.commits
  const commitsDelta =
    ct != null
      ? formatDelta(
          ct.current_total ?? total ?? 0,
          ct.previous_total ?? 0,
          compareMode,
        )
      : null
  const period = horizonPeriodPhrase(timeHorizon)
  const winD = horizonToWindowDays(timeHorizon)
  const evidenceHref =
    timeHorizon === 'week'
      ? '/api/chart-data/overview'
      : `/api/chart-data/overview?horizon=${encodeURIComponent(timeHorizon)}`

  return (
    <section className="le-cc-section" aria-labelledby="le-cc-what-changed">
      <h2 id="le-cc-what-changed" className="le-cc-section__title">
        {whatChangedSectionTitle(timeHorizon)}
      </h2>
      <p className="le-cc-section__lead">
        Delivery pulse from git activity ({period}). Cross-repository charts and the raw JSON bundle are optional
        inspect surfaces — open them from <strong>Settings (gear)</strong> → Inspect &amp; advanced, or expand below.
      </p>
      <TechnicalDetails summary="Inspect: advanced reporting and raw chart bundle" className="forge-support">
        <p style={{ margin: '0 0 0.5rem', fontSize: '0.88rem' }}>
          <Link className="le-cc-link" to="/overview/charts">
            {STUDIO_VOCAB.advancedReporting}
          </Link>{' '}
          (same page as gear menu). Raw bundle:{' '}
          <a href={evidenceHref}>
            <code>{evidenceHref}</code>
          </a>
          .
        </p>
      </TechnicalDetails>
      {chartError ? (
        <StatePanel
          variant="error"
          density="compact"
          title="Overview metrics unavailable"
          description={
            <>
              We could not load the chart-data bundle for this time horizon. Portfolio rollups and commit
              totals may be incomplete until the API responds.
            </>
          }
          aiRecovery={{
            prompt: 'Overview metrics on the Lenses home page failed to load. What should I check next?',
            label: 'Ask Chat about metrics recovery',
          }}
          actions={
            <>
              <Link className="le-btn le-btn--primary le-btn--small" to="/overview/charts">
                Advanced reporting
              </Link>
              <a className="le-btn le-btn--small" href={evidenceHref}>
                Raw JSON bundle
              </a>
            </>
          }
        />
      ) : (
        <div
          className={
            overviewDataLoading
              ? 'le-cc-what-changed__shell le-cc-what-changed__shell--loading'
              : 'le-cc-what-changed__shell'
          }
        >
          {overviewDataLoading ? (
            <div className="le-cc-what-changed__blade le-loading-blade" aria-hidden />
          ) : null}
          <div className="le-cc-what-changed__shell-inner">
            <p className="le-cc-metric le-cc-metric--row">
              <strong className={tierToClass(ct?.tier)}>
                {total != null ? total : overviewDataLoading ? '…' : '—'}
              </strong>
              {commitsDelta ? <DeltaPill {...commitsDelta} compareMode={compareMode} /> : null}
              <span className="le-cc-metric__label"> commits across workspace ({period})</span>
            </p>
            {top.length === 0 ? (
              <p className="le-cc-section__empty">
                {overviewDataLoading
                  ? 'Loading per-repo lines-added activity…'
                  : 'No per-repo lines-added activity in this bundle.'}
              </p>
            ) : (
              <div className="le-table-wrap le-cc-table-wrap">
                <table className="le-table le-cc-table">
                  <thead>
                    <tr>
                      <th>Repository</th>
                      <th>
                        Lines added ({winD}d) <span className="le-muted">/ Δ</span>
                      </th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {top.map((row) => {
                      const prev = lookupPrevLinesAdded(chart, row.name)
                      const delta =
                        typeof prev === 'number'
                          ? formatDelta(row.linesAdded, prev, compareMode)
                          : null
                      return (
                        <tr key={row.name}>
                          <td className="le-name">
                            <Link to={`/projects/${encodeURIComponent(row.name)}`}>{row.name}</Link>
                          </td>
                          <td className="le-mono">
                            {row.linesAdded.toLocaleString()}
                            {delta && compareMode === 'previous_period' ? (
                              <span className="le-table-delta-inline">
                                {' '}
                                ({delta.text})
                              </span>
                            ) : null}
                          </td>
                          <td>
                            <Link className="le-cc-link" to={`/projects/${encodeURIComponent(row.name)}`}>
                              Open dashboard
                            </Link>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  )
}
