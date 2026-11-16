import { useEffect, useMemo } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import type { WorkspaceChild } from '../../api/workspace'
import {
  sumCommitDailySevenDay,
  topReposByLinesAdded,
  type OverviewChartPayload,
} from '../../api/chartOverview'
import { useShellChrome } from '../../context/ShellChromeContext'
import { useWorkspace } from '../../context/WorkspaceContext'
import { useResilientJsonBlock } from '../../hooks/useResilientJsonBlock'
import { buildRepoPortfolioRows } from '../../lib/workspacePortfolio'
import { parsePortfolioTableFilter } from '../../lib/portfolioDrilldown'
import { DataResilienceBar, StatePanel } from '../page'
import { PortfolioProjectsTable } from './PortfolioProjectsTable'

function formatResolved(iso: string | undefined) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short',
    })
  } catch {
    return iso
  }
}

function sortChildrenForOther(children: WorkspaceChild[]) {
  const list = [...children]
  return list.sort((a, b) => {
    const an = String(a.name || '')
    const bn = String(b.name || '')
    const aNoise = an === '__pycache__' || an === 'node_modules'
    const bNoise = bn === '__pycache__' || bn === 'node_modules'
    if (aNoise !== bNoise) return aNoise ? 1 : -1
    const ag = a.is_git ? 1 : 0
    const bg = b.is_git ? 1 : 0
    if (ag !== bg) return bg - ag
    return an.localeCompare(bn, undefined, { sensitivity: 'base' })
  })
}

export function ProjectsArtifactsPortfolio() {
  const { state } = useWorkspace()
  const [sp] = useSearchParams()
  const tableFilter = parsePortfolioTableFilter(sp.get('filter'))
  const { timeHorizon, beginOverviewDataLoad, endOverviewDataLoad } = useShellChrome()

  const overviewPath = useMemo(() => {
    const q = timeHorizon === 'week' ? '' : `?horizon=${encodeURIComponent(timeHorizon)}`
    return `/api/chart-data/overview${q}`
  }, [timeHorizon])

  const chartBlock = useResilientJsonBlock<OverviewChartPayload>(overviewPath, {
    snapshotKey: `overview-charts:${timeHorizon}`,
    refreshKey: state?.resolved_at,
  })

  const chart = chartBlock.data
  const chartUsable = chart != null

  useEffect(() => {
    if (chartBlock.phase !== 'loading') return undefined
    beginOverviewDataLoad()
    return () => endOverviewDataLoad()
  }, [chartBlock.phase, beginOverviewDataLoad, endOverviewDataLoad])

  const portfolioRows = useMemo(() => buildRepoPortfolioRows(state, chart), [state, chart])

  const childByName = useMemo(() => {
    const m = new Map<string, WorkspaceChild>()
    for (const ch of state?.children ?? []) {
      m.set(String(ch.name ?? '').trim(), ch)
    }
    return m
  }, [state?.children])

  const summary = useMemo(() => {
    let atRisk = 0
    let watch = 0
    let healthy = 0
    for (const r of portfolioRows) {
      if (r.health === 'at_risk') atRisk += 1
      else if (r.health === 'watch') watch += 1
      else healthy += 1
    }
    return { atRisk, watch, healthy, total: portfolioRows.length }
  }, [portfolioRows])

  const commits7d = chartUsable && chart ? sumCommitDailySevenDay(chart) : null
  const topActivity = chartUsable && chart ? topReposByLinesAdded(chart, 10) : []

  const showChartStale = chartBlock.phase === 'stale'
  const showChartError = chartBlock.phase === 'error' && !chartUsable

  const nonGit = useMemo(() => {
    const list = (state?.children ?? []).filter((c) => !c.is_git)
    return sortChildrenForOther(list)
  }, [state?.children])

  if (!state) return null

  return (
    <>
      <header className="le-portfolio-header">
        <h1 className="le-h1">Portfolio snapshot</h1>
        <p className="le-portfolio-header__sub">
          Directory and decision surface for repositories in this workspace — health, confidence, standards,
          and activity. Workspace scan: {formatResolved(state.resolved_at)}.
        </p>
      </header>

      {showChartStale ? (
        <DataResilienceBar
          variant="stale"
          failure={chartBlock.failure}
          snapshotAtMs={chartBlock.snapshotFetchedAt}
          snapshotTimeLabel={chartBlock.snapshotTimeLabel}
          snapshotAgeLabel={chartBlock.snapshotAgeLabel}
          onRetry={chartBlock.retry}
          extraActions={
            <Link className="le-btn le-btn--small" to="/overview/charts">
              Advanced reporting
            </Link>
          }
        />
      ) : null}
      {showChartError ? (
        <DataResilienceBar
          variant="error"
          failure={chartBlock.failure}
          snapshotAtMs={null}
          snapshotTimeLabel={null}
          snapshotAgeLabel={null}
          onRetry={chartBlock.retry}
          extraActions={
            <Link className="le-btn le-btn--small" to="/overview/charts">
              Advanced reporting
            </Link>
          }
        />
      ) : null}

      <section className="le-portfolio-section" aria-labelledby="le-portfolio-summary-h">
        <h2 id="le-portfolio-summary-h" className="le-portfolio-section__title">
          Portfolio summary
        </h2>
        <div className="le-portfolio-kpis">
          <div className="le-portfolio-kpi">
            <span className="le-portfolio-kpi__value">{summary.total}</span>
            <span className="le-portfolio-kpi__label">Git repositories</span>
          </div>
          <div className="le-portfolio-kpi">
            <span className="le-portfolio-kpi__value le-portfolio-kpi__value--risk">{summary.atRisk}</span>
            <span className="le-portfolio-kpi__label">At risk</span>
          </div>
          <div className="le-portfolio-kpi">
            <span className="le-portfolio-kpi__value le-portfolio-kpi__value--watch">{summary.watch}</span>
            <span className="le-portfolio-kpi__label">Watch</span>
          </div>
          <div className="le-portfolio-kpi">
            <span className="le-portfolio-kpi__value le-portfolio-kpi__value--ok">{summary.healthy}</span>
            <span className="le-portfolio-kpi__label">Healthy</span>
          </div>
          <div className="le-portfolio-kpi">
            <span className="le-portfolio-kpi__value">{commits7d != null ? commits7d : '—'}</span>
            <span className="le-portfolio-kpi__label">Commits (7d, workspace)</span>
          </div>
        </div>
      </section>

      {summary.atRisk + summary.watch > 0 && (
        <section className="le-portfolio-callout" aria-labelledby="le-portfolio-attention-h">
          <h2 id="le-portfolio-attention-h" className="le-portfolio-callout__title">
            Projects needing attention
          </h2>
          <p className="le-portfolio-callout__body">
            {summary.atRisk + summary.watch} repo(s) flagged as at risk or watch (standards, planning
            artifacts, or working tree). Use the table filter <strong>Attention</strong> to focus the list.
          </p>
        </section>
      )}

      <PortfolioProjectsTable
        rows={portfolioRows}
        childByName={childByName}
        initialFilter={tableFilter}
      />

      <section className="le-portfolio-section" aria-labelledby="le-portfolio-recent-h">
        <h2 id="le-portfolio-recent-h" className="le-portfolio-section__title">
          Recent changes by project
        </h2>
        <p className="le-portfolio-section__lead">
          Delivery pulse from git activity (lines added, 7 days). Same source as workspace charts — not a
          full commit log.
        </p>
        {!chartUsable && chartBlock.phase === 'loading' ? (
          <p className="forge-support">Loading activity bundle…</p>
        ) : !chartUsable && showChartError ? (
          <p className="forge-support">
            Recent activity needs the workspace chart bundle. Use <strong>Retry</strong> above or open workspace
            charts.
          </p>
        ) : topActivity.length === 0 ? (
          <StatePanel
            variant="empty"
            density="compact"
            title="No recent lines-added signal"
            description="Either there was no activity in the window or the workspace has no git repos with data in this bundle."
            actions={
              <Link className="le-btn le-btn--small" to="/projects">
                Browse projects
              </Link>
            }
          />
        ) : (
          <div className="le-table-wrap le-portfolio-table-wrap">
            <table className="le-table le-portfolio-table">
              <thead>
                <tr>
                  <th>Repository</th>
                  <th>Lines added (7d)</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {topActivity.map((row) => (
                  <tr key={row.name}>
                    <td className="le-name">
                      <Link to={`/projects/${encodeURIComponent(row.name)}`}>{row.name}</Link>
                    </td>
                    <td className="le-mono">{row.linesAdded.toLocaleString()}</td>
                    <td>
                      <Link className="le-cc-link" to={`/projects/${encodeURIComponent(row.name)}`}>
                        Open dashboard
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {nonGit.length > 0 && (
        <details className="le-portfolio-other">
          <summary>Other workspace entries ({nonGit.length})</summary>
          <p className="forge-support">Non-git folders — browse or open as generic project links.</p>
          <ul className="le-list le-portfolio-other-list">
            {nonGit.map((c) => (
              <li key={c.name}>
                <Link to={`/projects/${encodeURIComponent(c.name)}`}>{c.name}</Link>
                <span className="le-muted"> · folder</span>
              </li>
            ))}
          </ul>
        </details>
      )}
    </>
  )
}
