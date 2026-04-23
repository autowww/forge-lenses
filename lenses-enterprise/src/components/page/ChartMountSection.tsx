import { Link } from 'react-router-dom'
import type { ResilientJsonBlockResult } from '../../hooks/useResilientJsonBlock'
import { ForgeChartMount } from '../ForgeChartMount'
import { ChartFallbackSummary } from './ChartFallbackSummary'
import { DataResilienceBar } from './DataResilienceBar'
import { StatePanel } from './StatePanel'

function chartHasRenderableData(chartKind: string, payload: Record<string, unknown>): boolean {
  const charts = payload.charts as Record<string, unknown> | undefined
  if (!charts || typeof charts !== 'object') return false
  const nSeries = (block: { series?: unknown[] } | undefined) =>
    Array.isArray(block?.series) && block.series.length > 0
  const nRows = (block: { rows?: unknown[] } | undefined) => Array.isArray(block?.rows) && block.rows.length > 0

  switch (chartKind) {
    case 'commit_daily':
      return nSeries(charts.commit_daily as { series?: unknown[] })
    case 'commit_weekly':
      return nSeries(charts.commit_weekly as { series?: unknown[] })
    case 'loc_added_horizontal':
      return nRows(charts.loc_added_horizontal as { rows?: unknown[] })
    case 'loc_total_bars':
      return nRows(charts.loc_total_bars as { rows?: unknown[] })
    case 'loc_share_donut':
      return nRows(charts.loc_share_donut as { rows?: unknown[] })
    case 'compliance_bars':
      return nRows(charts.compliance_bars as { rows?: unknown[] })
    case 'extension_heatmap': {
      const h = charts.extension_heatmap as { extensions?: unknown[] } | undefined
      return Array.isArray(h?.extensions) && h.extensions.length > 0
    }
    case 'contributors':
      return nRows(charts.contributors as { rows?: unknown[] })
    case 'submodule_layout': {
      const s = charts.submodule_layout as { paths?: unknown[] } | undefined
      return Array.isArray(s?.paths) && s.paths.length > 0
    }
    default:
      return true
  }
}

export type ChartMountSectionProps = {
  title: string
  chartKind: string
  dataUrl: string
  /** Adds a project dashboard link to error recovery when chart data fails to load. */
  recoveryProjectName?: string
  /** Shared resilient fetch state for all blocks on this page (one JSON bundle per endpoint). */
  chartBundle: ResilientJsonBlockResult<Record<string, unknown>>
}

/**
 * Chart block: uses shared bundle fetch + snapshot fallback; avoids repeating full-page error panels.
 */
export function ChartMountSection({
  title,
  chartKind,
  dataUrl,
  recoveryProjectName,
  chartBundle: b,
}: ChartMountSectionProps) {
  const proj = recoveryProjectName?.trim()
  const payload = b.data

  const recovery = proj ? (
    <Link className="le-btn le-btn--small" to={`/projects/${encodeURIComponent(proj)}`}>
      Project dashboard
    </Link>
  ) : (
    <Link className="le-btn le-btn--small" to="/">
      Workspace overview
    </Link>
  )

  if (b.phase === 'loading' && !payload) {
    return (
      <section className="le-panel forge-card mb-4" style={{ marginBottom: '1rem' }} data-ks-chart-wrap={chartKind}>
        <h3 className="le-panel__title" style={{ fontSize: '0.95rem', marginBottom: '0.5rem' }}>
          {title}
        </h3>
        <StatePanel
          variant="loading"
          density="compact"
          title="Loading chart data"
          description="Fetching the JSON bundle this visualization shares with other blocks on the page."
        />
      </section>
    )
  }

  if (payload && typeof payload === 'object' && payload.error === 'not_git') {
    return (
      <section className="le-panel forge-card mb-4" style={{ marginBottom: '1rem' }} data-ks-chart-wrap={chartKind}>
        <h3 className="le-panel__title" style={{ fontSize: '0.95rem', marginBottom: '0.5rem' }}>
          {title}
        </h3>
        <StatePanel
          variant="empty"
          density="compact"
          title="Not a git repository"
          description="This folder has no `.git` directory in the workspace scan, so git-backed charts are not generated. Pick a git repository from Projects, or run a workspace scan."
          actions={
            <>
              <Link className="le-btn le-btn--small le-btn--primary" to="/projects">
                All projects
              </Link>
              {proj ? (
                <a className="le-btn le-btn--small" href={`/projects/${encodeURIComponent(proj)}`}>
                  Open classic project page
                </a>
              ) : null}
            </>
          }
        />
      </section>
    )
  }

  if (b.phase === 'error' && !payload) {
    return (
      <section className="le-panel forge-card mb-4" style={{ marginBottom: '1rem' }} data-ks-chart-wrap={chartKind}>
        <h3 className="le-panel__title" style={{ fontSize: '0.95rem', marginBottom: '0.5rem' }}>
          {title}
        </h3>
        <DataResilienceBar
          variant="error"
          failure={b.failure}
          snapshotAtMs={null}
          snapshotTimeLabel={null}
          snapshotAgeLabel={null}
          onRetry={b.retry}
          extraActions={recovery}
        />
      </section>
    )
  }

  if (b.phase === 'stale' && payload) {
    return (
      <section className="le-panel forge-card mb-4" style={{ marginBottom: '1rem' }} data-ks-chart-wrap={chartKind}>
        <h3 className="le-panel__title" style={{ fontSize: '0.95rem', marginBottom: '0.5rem' }}>
          {title}
        </h3>
        <DataResilienceBar
          variant="stale"
          failure={b.failure}
          snapshotAtMs={b.snapshotFetchedAt}
          snapshotTimeLabel={b.snapshotTimeLabel}
          snapshotAgeLabel={b.snapshotAgeLabel}
          onRetry={b.retry}
          extraActions={recovery}
        />
        <ChartFallbackSummary chartKind={chartKind} bundle={payload} />
      </section>
    )
  }

  if (payload && typeof payload === 'object' && !chartHasRenderableData(chartKind, payload)) {
    return (
      <section className="le-panel forge-card mb-4" style={{ marginBottom: '1rem' }} data-ks-chart-wrap={chartKind}>
        <h3 className="le-panel__title" style={{ fontSize: '0.95rem', marginBottom: '0.5rem' }}>
          {title}
        </h3>
        <StatePanel
          variant="empty"
          density="compact"
          title="No chart data in this bundle"
          description="The API returned a payload with no series or rows for this chart. Try another time horizon, run a workspace scan, or open the raw JSON link from the overview page."
          actions={recovery}
        />
        <ChartFallbackSummary chartKind={chartKind} bundle={payload} />
      </section>
    )
  }

  return <ForgeChartMount title={title} chartKind={chartKind} dataUrl={dataUrl} />
}
