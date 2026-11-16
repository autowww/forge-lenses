/**
 * Text fallback when forge-data-charts cannot run but we still hold JSON (e.g. stale snapshot).
 */

function rowCount(rows: unknown): number {
  return Array.isArray(rows) ? rows.length : 0
}

export type ChartFallbackSummaryProps = {
  chartKind: string
  bundle: Record<string, unknown>
}

export function ChartFallbackSummary({ chartKind, bundle }: ChartFallbackSummaryProps) {
  const charts = bundle.charts as Record<string, unknown> | undefined
  const lines = summarizeChartBlock(chartKind, charts, bundle)
  if (lines.length === 0) {
    return (
      <p className="le-chart-fallback-summary forge-support">
        No text summary available for this chart type in the saved bundle.
      </p>
    )
  }
  return (
    <div className="le-chart-fallback-summary">
      <p className="le-chart-fallback-summary__title forge-support">Snapshot summary (chart not rendered)</p>
      <ul className="le-chart-fallback-summary__list">
        {lines.map((t) => (
          <li key={t}>{t}</li>
        ))}
      </ul>
    </div>
  )
}

function summarizeChartBlock(
  chartKind: string,
  charts: Record<string, unknown> | undefined,
  bundle: Record<string, unknown>,
): string[] {
  if (bundle.error === 'not_git') {
    return ['This path is not a git repository — chart data is not produced for non-git folders.']
  }
  if (!charts) return []

  const out: string[] = []

  switch (chartKind) {
    case 'commit_weekly': {
      const block = charts.commit_weekly as { series?: unknown[] } | undefined
      const n = rowCount(block?.series)
      out.push(`${n} weekly commit bucket(s) in bundle.`)
      break
    }
    case 'commit_daily': {
      const block = charts.commit_daily as { series?: unknown[] } | undefined
      const n = rowCount(block?.series)
      out.push(`${n} day(s) of commit counts in bundle.`)
      break
    }
    case 'contributors': {
      const block = charts.contributors as { rows?: unknown[] } | undefined
      const n = rowCount(block?.rows)
      out.push(`${n} contributor row(s) in bundle.`)
      break
    }
    case 'extension_heatmap': {
      const block = charts.extension_heatmap as { extensions?: unknown[]; tracked_files?: number } | undefined
      const extN = rowCount(block?.extensions)
      const tf = block?.tracked_files
      out.push(
        `${extN} file-type bucket(s)` + (typeof tf === 'number' ? ` · ~${tf.toLocaleString()} tracked files` : ''),
      )
      break
    }
    case 'compliance_bars': {
      const block = charts.compliance_bars as { rows?: unknown[] } | undefined
      out.push(`${rowCount(block?.rows)} compliance row(s) in bundle.`)
      break
    }
    case 'submodule_layout': {
      const block = charts.submodule_layout as { paths?: unknown[]; project_label?: string } | undefined
      const paths = Array.isArray(block?.paths) ? block.paths.length : 0
      const label = block?.project_label != null ? String(block.project_label) : 'project'
      out.push(`${paths} submodule path(s) recorded for ${label}.`)
      break
    }
    case 'loc_added_horizontal': {
      const block = charts.loc_added_horizontal as { rows?: unknown[] } | undefined
      out.push(`${rowCount(block?.rows)} repository row(s) with lines-added values.`)
      break
    }
    case 'loc_total_bars': {
      const block = charts.loc_total_bars as { rows?: unknown[] } | undefined
      out.push(`${rowCount(block?.rows)} repository row(s) in approximate size chart.`)
      break
    }
    case 'loc_share_donut': {
      const block = charts.loc_share_donut as { rows?: unknown[]; top_n?: number } | undefined
      const n = rowCount(block?.rows)
      const cap = block?.top_n
      out.push(
        `${n} slice(s) in line-share chart` + (typeof cap === 'number' ? ` (top ${cap} shown when capped)` : ''),
      )
      break
    }
    default:
      break
  }

  return out
}
