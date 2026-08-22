import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import type { CompareModeId, TimeHorizonId } from '../../context/ShellChromeContext'
import type { OverviewChartPayload } from '../../api/chartOverview'
import { horizonToWindowDays } from '../../api/chartOverview'
import { formatDelta, heatIntensityClass, tierToClass } from '../../lib/kpiTrendUi'
import type { RepoPortfolioRow } from '../../lib/workspacePortfolio'
import { StatePanel } from '../page'

function healthBadge(health: RepoPortfolioRow['health']): string {
  switch (health) {
    case 'healthy':
      return 'le-cc-health le-cc-health--healthy'
    case 'watch':
      return 'le-cc-health le-cc-health--watch'
    case 'at_risk':
      return 'le-cc-health le-cc-health--at-risk'
    default:
      return 'le-cc-health'
  }
}

function healthLabel(health: RepoPortfolioRow['health']): string {
  switch (health) {
    case 'healthy':
      return 'Healthy'
    case 'watch':
      return 'Watch'
    case 'at_risk':
      return 'At risk'
    default:
      return health
  }
}

type Props = {
  rows: RepoPortfolioRow[]
  chart: OverviewChartPayload | null
  compareMode: CompareModeId
  timeHorizon: TimeHorizonId
  overviewDataLoading?: boolean
}

export function PortfolioHealth({
  rows,
  chart,
  compareMode,
  timeHorizon,
  overviewDataLoading = false,
}: Props) {
  const winD = horizonToWindowDays(timeHorizon)

  const footer = useMemo(() => {
    const riskSum = rows.reduce((s, r) => s + r.riskScore, 0)
    const stdScores = rows
      .map((r) => r.standardsScore)
      .filter((x): x is number => x != null)
    const stdAvg =
      stdScores.length > 0 ? stdScores.reduce((a, b) => a + b, 0) / stdScores.length : null
    const rmSum = rows.reduce((s, r) => s + r.roadmapCount, 0)
    const wbsSum = rows.reduce((s, r) => s + r.wbsCount, 0)
    const la = chart?.kpi_trends?.lines_added
    const linesTotal = typeof la?.current_total === 'number' ? la.current_total : null
    const linesPrev = typeof la?.previous_total === 'number' ? la.previous_total : null
    const linesTier = typeof la?.tier === 'string' ? la.tier : undefined
    return { riskSum, stdAvg, rmSum, wbsSum, linesTotal, linesPrev, linesTier }
  }, [rows, chart])

  const workspaceLinesDelta =
    footer.linesTotal != null &&
    footer.linesPrev != null &&
    compareMode === 'previous_period'
      ? formatDelta(footer.linesTotal, footer.linesPrev, compareMode)
      : null

  return (
    <section className="le-cc-section" aria-labelledby="le-cc-portfolio-health">
      <h2 id="le-cc-portfolio-health" className="le-cc-section__title">
        Portfolio health
      </h2>
      <p className="le-cc-section__lead">
        By repository (initiative/product rollups ship later). Sorted by risk first — higher score means
        more factors flagged.
      </p>
      {rows.length === 0 ? (
        <StatePanel
          variant="empty"
          density="compact"
          title="No git repositories in this workspace"
          description="This scan did not find git roots to score. Add or open a workspace root that contains repos, then rescan from the overview."
          actions={
            <Link className="le-btn le-btn--small" to="/">
              Back to overview
            </Link>
          }
        />
      ) : (
        <div
          className={`le-table-wrap le-cc-table-wrap${
            overviewDataLoading ? ' le-cc-table-wrap--chart-loading' : ''
          }`}
        >
          {overviewDataLoading ? (
            <div className="le-cc-table-wrap__blade le-loading-blade" aria-hidden />
          ) : null}
          <table className="le-table le-cc-table">
            <thead>
              <tr>
                <th>Repository</th>
                <th>Health</th>
                <th>Risk score</th>
                <th>Standards</th>
                <th>Roadmaps</th>
                <th>WBS</th>
                <th>
                  {winD}d lines <span className="le-muted">/ Δ</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.name}>
                  <td className="le-name">
                    <Link to={`/projects/${encodeURIComponent(r.name)}`}>{r.name}</Link>
                  </td>
                  <td>
                    <span className={healthBadge(r.health)}>{healthLabel(r.health)}</span>
                  </td>
                  <td className="le-mono">{r.riskScore}</td>
                  <td>
                    {r.standardsScore != null ? (
                      <>
                        <span className="le-mono">{r.standardsScore}</span>
                        {r.standardsTier ? (
                          <span className="le-muted"> · {r.standardsTier}</span>
                        ) : null}
                      </>
                    ) : (
                      '—'
                    )}
                  </td>
                  <td className="le-mono">{r.roadmapCount}</td>
                  <td className="le-mono">{r.wbsCount}</td>
                  <td className="le-mono">
                    {r.linesAdded7d != null ? (
                      <>
                        <span
                          className={`${tierToClass(r.linesTier ?? undefined)} ${heatIntensityClass(r.linesAdded7d, r.linesMedianPrior6 ?? null)}`.trim()}
                          title={
                            typeof r.linesMedianPrior6 === 'number'
                              ? `Median of prior six periods: ${r.linesMedianPrior6}`
                              : undefined
                          }
                        >
                          {r.linesAdded7d.toLocaleString()}
                        </span>
                        {r.linesPrev7d != null && compareMode === 'previous_period' ? (
                          <span className="le-table-delta-inline">
                            {' '}
                            (
                            {formatDelta(r.linesAdded7d, r.linesPrev7d, compareMode)?.text ?? '—'}
                            )
                          </span>
                        ) : null}
                      </>
                    ) : (
                      '—'
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot className="le-cc-table__foot">
              <tr>
                <td className="le-name le-cc-table__foot-label">
                  <strong>Workspace</strong>
                </td>
                <td>—</td>
                <td
                  className="le-mono"
                  title="Sum of per-repository risk scores (not a recomputed index)."
                >
                  {footer.riskSum}
                </td>
                <td className="le-mono">
                  {footer.stdAvg != null ? Math.round(footer.stdAvg * 10) / 10 : '—'}
                </td>
                <td className="le-mono">{footer.rmSum}</td>
                <td className="le-mono">{footer.wbsSum}</td>
                <td className="le-mono">
                  {footer.linesTotal != null ? (
                    <>
                      <span className={tierToClass(footer.linesTier)}>
                        {footer.linesTotal.toLocaleString()}
                      </span>
                      {workspaceLinesDelta ? (
                        <span className="le-table-delta-inline">
                          {' '}
                          ({workspaceLinesDelta.text})
                        </span>
                      ) : null}
                    </>
                  ) : (
                    '—'
                  )}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}
    </section>
  )
}
