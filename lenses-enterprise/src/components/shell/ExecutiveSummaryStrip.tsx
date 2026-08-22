import { useRef, useState } from 'react'
import { useWorkspace } from '../../context/WorkspaceContext'
import {
  commitsKpiLabel,
  linesAddedKpiLabel,
  sparklinePeriodHint,
  sparklinePeriodTotals,
  sumCommitDailySevenDay,
  workspaceLocTotal,
} from '../../api/chartOverview'
import type { WorkspaceChild } from '../../api/workspace'
import { useOverviewTelemetry } from '../../context/OverviewTelemetryContext'
import { useShellChrome } from '../../context/ShellChromeContext'
import { formatDelta, heatIntensityClass, tierToClass } from '../../lib/kpiTrendUi'
import { KpiMetricTile, KpiSnapshotTile } from './KpiMetricTile'
import { OverviewKpiFlyout, type OverviewKpiFlyoutKind } from './OverviewKpiFlyout'

function formatResolvedShort(iso: string | undefined): string {
  if (!iso) return '—'
  try {
    const d = new Date(iso)
    return d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
  } catch {
    return iso
  }
}

function confidenceFromResolved(iso: string | undefined): { label: string; hint: string } {
  if (!iso) return { label: 'Unknown', hint: 'No timestamp on workspace scan.' }
  const t = new Date(iso).getTime()
  if (Number.isNaN(t)) return { label: 'Unknown', hint: 'Could not parse resolved time.' }
  const ageMin = (Date.now() - t) / 60000
  if (ageMin < 6) return { label: 'High', hint: 'Scan finished in the last few minutes.' }
  if (ageMin < 60) return { label: 'Medium', hint: 'Scan is from the last hour.' }
  return { label: 'Medium', hint: 'Refresh for the latest workspace snapshot.' }
}

function countGit(children: WorkspaceChild[]): number {
  return children.filter((c) => c.is_git).length
}

function avgCompliance(children: WorkspaceChild[]): number | null {
  const scores = children
    .map((c) => c.standards_compliance?.score)
    .filter((s): s is number => typeof s === 'number')
  if (scores.length === 0) return null
  return Math.round(scores.reduce((a, b) => a + b, 0) / scores.length)
}

export function ExecutiveSummaryStrip({ compact = false }: { compact?: boolean }) {
  const { state } = useWorkspace()
  const { compareMode, timeHorizon, overviewDataLoading } = useShellChrome()
  const { payload, loading, error: chartErr, jobHint, progress } = useOverviewTelemetry()
  const [flyout, setFlyout] = useState<OverviewKpiFlyoutKind | null>(null)
  const commitsRef = useRef<HTMLDivElement | null>(null)
  const linesRef = useRef<HTMLDivElement | null>(null)
  const standardsRef = useRef<HTMLDivElement | null>(null)

  if (!state) return null

  const children = Array.isArray(state.children) ? state.children : []
  const gitN = countGit(children)
  const sitesN = (state.websites ?? []).length
  const planArtifacts = (state.wbs ?? []).length + (state.roadmaps ?? []).length
  const conf = confidenceFromResolved(state.resolved_at)
  const complianceAvg = avgCompliance(children)

  const kt = payload?.kpi_trends
  const commitsTrend = kt?.commits
  const linesTrend = kt?.lines_added
  const snapGit = kt?.snapshots?.git_repos
  const snapSites = kt?.snapshots?.sites
  const snapPlan = kt?.snapshots?.plan_artifacts
  const snapStand = kt?.snapshots?.standards_avg

  const commits7d = chartErr ? null : sumCommitDailySevenDay(payload ?? {})
  const gitSpark = sparklinePeriodTotals(snapGit?.period_totals?.map((x) => Number(x)))
  const sitesSpark = sparklinePeriodTotals(snapSites?.period_totals?.map((x) => Number(x)))
  const planSpark = sparklinePeriodTotals(snapPlan?.period_totals?.map((x) => Number(x)))
  const commitSpark = chartErr ? [] : sparklinePeriodTotals(commitsTrend?.period_totals)
  const locSpark =
    chartErr ? [] : sparklinePeriodTotals(linesTrend?.period_totals?.map((x) => Number(x)))
  const standSpark = sparklinePeriodTotals(snapStand?.period_totals?.map((x) => Number(x)))

  const hintSpark =
    [gitSpark, sitesSpark, planSpark, commitSpark, locSpark, standSpark].find((s) => s.length >= 2) ??
    commitSpark

  const commitsDelta = formatDelta(
    commitsTrend?.current_total ?? commits7d ?? 0,
    commitsTrend?.previous_total ?? 0,
    compareMode,
  )
  const gitDelta =
    snapGit != null ? formatDelta(snapGit.current ?? gitN, snapGit.previous_total ?? 0, compareMode) : null
  const sitesDelta =
    snapSites != null
      ? formatDelta(snapSites.current ?? sitesN, snapSites.previous_total ?? 0, compareMode)
      : null
  const planDelta =
    snapPlan != null
      ? formatDelta(snapPlan.current ?? planArtifacts, snapPlan.previous_total ?? 0, compareMode)
      : null

  const locCurrent = linesTrend?.current_total
  const locDelta =
    linesTrend != null && typeof locCurrent === 'number'
      ? formatDelta(locCurrent, linesTrend.previous_total ?? 0, compareMode)
      : null

  const locTotalApprox = chartErr ? null : workspaceLocTotal(payload)

  const standVal = complianceAvg
  const standDelta =
    standVal != null &&
    snapStand != null &&
    typeof snapStand.previous_total === 'number'
      ? formatDelta(standVal, Math.round(snapStand.previous_total), compareMode)
      : null

  const dataLoading = overviewDataLoading || loading
  const commitsHeat =
    typeof commitsTrend?.current_total === 'number'
      ? heatIntensityClass(commitsTrend.current_total, commitsTrend.median_prior_6 ?? null)
      : ''
  const linesHeat =
    typeof locCurrent === 'number'
      ? heatIntensityClass(locCurrent, linesTrend?.median_prior_6 ?? null)
      : ''
  const standHeat =
    standVal != null
      ? heatIntensityClass(standVal, snapStand?.median_prior_6 ?? null)
      : ''

  const flyoutAnchor =
    flyout === 'commits' ? commitsRef : flyout === 'lines' ? linesRef : standardsRef

  return (
    <section
      className={
        dataLoading
          ? `le-kpi-strip${compact ? ' le-kpi-strip--compact' : ''} le-kpi-strip--loading`
          : `le-kpi-strip${compact ? ' le-kpi-strip--compact' : ''}`
      }
      aria-label="Executive summary"
      aria-describedby="le-kpi-period-hint"
    >
      {dataLoading ? (
        <div className="le-kpi-strip__blade le-loading-blade" aria-hidden />
      ) : null}
      <p className="le-kpi-strip__period-note" id="le-kpi-period-hint">
        {sparklinePeriodHint(timeHorizon, hintSpark)}
      </p>
      <div className="le-kpi-strip__grid">
        <KpiMetricTile
          label="Git repositories"
          spark={gitSpark}
          value={gitN}
          tierClass={tierToClass(snapGit?.tier)}
          delta={gitDelta}
          compareMode={compareMode}
          to="/projects"
          ariaLabel={`Git repositories: ${gitN}. Open project list.`}
        />
        <KpiMetricTile
          label="Published sites"
          spark={sitesSpark}
          value={sitesN}
          tierClass={tierToClass(snapSites?.tier)}
          delta={sitesDelta}
          compareMode={compareMode}
          to="/websites"
          ariaLabel={`Published sites: ${sitesN}. Open sites.`}
        />
        <KpiMetricTile
          label="Planning artifacts"
          spark={planSpark}
          value={planArtifacts}
          tierClass={tierToClass(snapPlan?.tier)}
          delta={planDelta}
          compareMode={compareMode}
          to="/plan"
          ariaLabel={`Planning artifacts: ${planArtifacts}. Open plans.`}
        />
        <div ref={commitsRef}>
          <KpiMetricTile
            label={commitsKpiLabel(timeHorizon)}
            spark={commitSpark}
            value={chartErr ? '—' : commits7d ?? '—'}
            tierClass={`${tierToClass(commitsTrend?.tier)} ${commitsHeat}`.trim()}
            delta={commitsDelta}
            compareMode={compareMode}
            onActivate={() => setFlyout('commits')}
            progress={progress}
            jobHint={jobHint}
            ariaLabel={
              chartErr
                ? 'Commits trend unavailable.'
                : `Commits: ${commits7d ?? '—'}. Open commits detail fly-out.`
            }
          />
        </div>
        <div ref={linesRef}>
          <KpiMetricTile
            label={linesAddedKpiLabel(timeHorizon)}
            spark={locSpark}
            value={
              chartErr || typeof locCurrent !== 'number'
                ? '—'
                : locCurrent.toLocaleString()
            }
            tierClass={`${tierToClass(linesTrend?.tier)} ${linesHeat}`.trim()}
            delta={locDelta}
            compareMode={compareMode}
            onActivate={() => setFlyout('lines')}
            progress={progress}
            jobHint={jobHint}
            ariaLabel={
              chartErr
                ? 'Lines added trend unavailable.'
                : `Lines added in workspace: ${typeof locCurrent === 'number' ? locCurrent.toLocaleString() : '—'}. Open lines detail fly-out.`
            }
          />
        </div>
        <KpiMetricTile
          label="LoC total (approx.)"
          spark={[]}
          value={locTotalApprox != null ? locTotalApprox.toLocaleString() : '—'}
          tierClass=""
          delta={null}
          compareMode={compareMode}
          to="/projects"
          progress={progress}
          jobHint={jobHint}
          ariaLabel={
            locTotalApprox != null
              ? `Approximate tracked lines in workspace: ${locTotalApprox.toLocaleString()}. Open projects for per-repository charts.`
              : 'Approximate workspace lines of code. Open projects portfolio.'
          }
        />
        <div ref={standardsRef}>
          <KpiMetricTile
            label="Standards (avg)"
            spark={standSpark}
            value={complianceAvg != null ? `${complianceAvg}` : '—'}
            tierClass={`${tierToClass(snapStand?.tier)} ${standHeat}`.trim()}
            delta={standDelta}
            compareMode={compareMode}
            onActivate={() => setFlyout('standards')}
            ariaLabel={
              complianceAvg != null
                ? `Standards average: ${complianceAvg}. Open standards detail fly-out.`
                : 'Standards average. Open standards detail fly-out.'
            }
          />
        </div>
        {!compact ? (
        <KpiSnapshotTile
          resolvedLabel={formatResolvedShort(state.resolved_at)}
          confidenceLine={`Confidence: ${conf.label}. ${conf.hint}`}
        />
        ) : null}
      </div>
      <OverviewKpiFlyout
        open={flyout != null}
        kind={flyout ?? 'commits'}
        onClose={() => setFlyout(null)}
        payload={payload}
        timeHorizon={timeHorizon}
        anchorRef={flyoutAnchor}
      />
    </section>
  )
}
