import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { horizonPeriodPhrase, kpiSparklineBucketExplanation } from '../api/chartOverview'
import { useShellChrome } from '../context/ShellChromeContext'
import { useResilientJsonBlock } from '../hooks/useResilientJsonBlock'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'
import { AdvancedSurfaceFraming, ChartMountSection, PageHeader, TechnicalDetails } from '../components/page'
import {
  ADMIN_INSPECT_COPY,
  ADVANCED_SURFACE_FRAMES,
  ROUTE_SUBTITLE,
  STUDIO_VOCAB,
} from '../nav/studioVisibleCopy'

export function OverviewChartsPage() {
  useLensesCopilotPage({
    route: 'advanced-reporting',
    defaultQuery: ADMIN_INSPECT_COPY.copilotAdvancedReporting,
  })
  const { timeHorizon } = useShellChrome()
  const apiUrl = useMemo(
    () =>
      timeHorizon === 'week'
        ? '/api/chart-data/overview'
        : `/api/chart-data/overview?horizon=${encodeURIComponent(timeHorizon)}`,
    [timeHorizon],
  )
  const chartBundle = useResilientJsonBlock<Record<string, unknown>>(apiUrl, {
    snapshotKey: `overview-chart-data:${timeHorizon}`,
  })
  const period = horizonPeriodPhrase(timeHorizon)
  const bucketHint = kpiSparklineBucketExplanation(timeHorizon)
  const blocks = useMemo(
    () => [
      { kind: 'commit_daily', title: `Commits by day (${period})` },
      { kind: 'loc_added_horizontal', title: `Lines added by repository (${period})` },
      { kind: 'loc_total_bars', title: 'Repository size (approx. LoC)' },
      { kind: 'loc_share_donut', title: 'Share of workspace lines' },
      { kind: 'compliance_bars', title: 'Compliance score by repository' },
      { kind: 'extension_heatmap', title: 'File types (workspace)' },
    ],
    [period],
  )

  return (
    <>
      <PageHeader
        title={STUDIO_VOCAB.advancedReporting}
        preface={
          <Link to="/" className="forge-support">
            ← Workspace overview
          </Link>
        }
        subtitle={ROUTE_SUBTITLE.workspaceChartsAdvanced}
      />
      <div style={{ marginTop: '-0.35rem', marginBottom: '0.75rem' }}>
        <AdvancedSurfaceFraming frame={ADVANCED_SURFACE_FRAMES.advancedReporting} />
      </div>
      <TechnicalDetails summary="Technical details (charts API and data bundle)">
        <p className="forge-support" style={{ margin: 0 }}>
          Charts load from <code>{apiUrl}</code> via <code>forge-data-charts.js</code>.
        </p>
        <p className="forge-support" style={{ margin: '0.5rem 0 0' }}>
          <strong>Time window:</strong> {period}. {bucketHint}
        </p>
      </TechnicalDetails>
      {blocks.map(({ kind, title }) => (
        <ChartMountSection key={kind} title={title} chartKind={kind} dataUrl={apiUrl} chartBundle={chartBundle} />
      ))}
    </>
  )
}
