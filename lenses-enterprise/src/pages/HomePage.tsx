import { useEffect, useMemo, useState } from 'react'
import { FlowArtifactsOnboardingCallout } from '../components/onboarding/FlowArtifactsOnboardingCallout'
import { recordPageFailure } from '../telemetry/studioTelemetry'
import { useWorkspace } from '../context/WorkspaceContext'
import type { WorkspaceChild } from '../api/workspace'
import { getOverviewChartPayload, type OverviewChartPayload } from '../api/chartOverview'
import { useShellChrome } from '../context/ShellChromeContext'
import {
  anyChargeArtifact,
  buildRepoPortfolioRows,
  pickRecentWins,
} from '../lib/workspacePortfolio'
import {
  WhatChangedThisWeek,
  PortfolioHealth,
  RiskOverview,
  StandardsAndTraceability,
  RecentWins,
  DecisionBacklog,
  QuickDrilldowns,
  WorkspaceAllEntriesTable,
  WorkspaceOperationalSnapshot,
  HomeLlmUsageBand,
} from '../components/home'
import { WorkspaceStateFallback } from '../components/WorkspaceStateFallback'
import {
  PageAiInsightCard,
  PageHeader,
  type PageHeaderStatusChip,
  PageSummaryBand,
  StatePanel,
  TechnicalDetails,
} from '../components/page'
import { STUDIO_VOCAB } from '../nav/studioVisibleCopy'
import { Link } from 'react-router-dom'
import { DocsHealthHomeBand } from '../components/docs-health/DocsHealthHomeBand'
import { DocsHealthActiveRunsBand } from '../components/docs-health/DocsHealthActiveRunsBand'
import { TraceabilityLaunchButton } from '../components/traceability'
import { StudioInlineAssist } from '../components/StudioInlineAssist'
import { DEMO_ORCHESTRATION_STORY_ID } from '../constants/demoOrchestration'
import { chargeMdCandidates } from '../lib/copilotPageEvidence'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'

function sortChildren(children: WorkspaceChild[]) {
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

export function HomePage() {
  const copilotOverview = useMemo(
    () => ({
      pageContextSummary: 'Forge Studio · Home overview · workspace snapshot',
      relatedMdRelPaths: chargeMdCandidates(undefined),
    }),
    [],
  )
  useLensesCopilotPage({
    route: 'overview',
    pageContextSummary: copilotOverview.pageContextSummary,
    relatedMdRelPaths: copilotOverview.relatedMdRelPaths,
  })
  const { state } = useWorkspace()
  const {
    timeHorizon,
    compareMode,
    beginOverviewDataLoad,
    endOverviewDataLoad,
    overviewDataLoading,
  } = useShellChrome()
  const [chart, setChart] = useState<OverviewChartPayload | null>(null)
  const [chartError, setChartError] = useState(false)

  useEffect(() => {
    let cancelled = false
    beginOverviewDataLoad()
    void getOverviewChartPayload(timeHorizon)
      .then((p) => {
        if (!cancelled) {
          setChart(p)
          setChartError(false)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setChart(null)
          setChartError(true)
        }
      })
      .finally(() => {
        endOverviewDataLoad()
      })
    return () => {
      cancelled = true
    }
  }, [state?.resolved_at, timeHorizon, beginOverviewDataLoad, endOverviewDataLoad])

  useEffect(() => {
    if (chartError) recordPageFailure('home_overview_charts', 'overview chart payload failed')
  }, [chartError])

  const portfolioRows = useMemo(
    () => buildRepoPortfolioRows(state, chart),
    [state, chart],
  )

  const wins = useMemo(() => pickRecentWins(portfolioRows, 5), [portfolioRows])

  const sorted = useMemo(() => {
    if (!state?.children) return []
    return sortChildren(Array.isArray(state.children) ? state.children : [])
  }, [state])

  if (!state) return <WorkspaceStateFallback />

  const websites = state.websites ?? []
  const hasCharge = anyChargeArtifact(state)

  const statusChips: PageHeaderStatusChip[] = []
  if (chartError) statusChips.push({ label: 'Charts unavailable', tone: 'warn' })
  else if (overviewDataLoading) statusChips.push({ label: 'Loading charts…', tone: 'muted' })
  else if (chart) statusChips.push({ label: 'Signals ready', tone: 'ok' })

  return (
    <>
      <PageHeader
        title={STUDIO_VOCAB.overview}
        purpose={`Scan-first control tower — not ${STUDIO_VOCAB.plan} editing. See repos, signals, and what moved.`}
        freshness={
          state.resolved_at ? (
            <>
              Last scan: <time dateTime={state.resolved_at}>{formatResolved(state.resolved_at)}</time>
            </>
          ) : (
            'Last scan: not recorded'
          )
        }
        statusChips={statusChips}
        primaryAction={
          <TraceabilityLaunchButton
            rootId={DEMO_ORCHESTRATION_STORY_ID}
            label="Trace sample story"
            title="Open orchestration graph: planning → code → CI → release → evidence (demo seed)"
          />
        }
        secondaryMenuItems={[
          { key: 'today', label: `Open ${STUDIO_VOCAB.today}`, to: '/plan?tab=today' },
          { key: 'boards', label: STUDIO_VOCAB.boards, to: '/board' },
          { key: 'projects', label: STUDIO_VOCAB.projects, to: '/projects' },
        ]}
      />

      <TechnicalDetails summary="What this overview is for" defaultOpen={false}>
        <p className="forge-support">
          Use this page to spot drift and charge signals across repositories. When you need backlog edits or delivery
          execution, jump to {STUDIO_VOCAB.today}, {STUDIO_VOCAB.boards}, or {STUDIO_VOCAB.plan} from the header menu or
          Quick assist.
        </p>
      </TechnicalDetails>

      <PageSummaryBand aria-label="Workspace summary">
        <WorkspaceOperationalSnapshot
          rows={portfolioRows}
          sitesCount={websites.length}
          hasChargeArtifact={hasCharge}
          scanLabel={formatResolved(state.resolved_at)}
        />
        <QuickDrilldowns />
      </PageSummaryBand>

      <HomeLlmUsageBand />

      <DocsHealthHomeBand />

      <DocsHealthActiveRunsBand />

      <StudioInlineAssist />

      <FlowArtifactsOnboardingCallout />

      <PageAiInsightCard
        whatChanged={
          compareMode === 'previous_period'
            ? `Comparing this ${timeHorizon} to the previous period.`
            : `Horizon: ${timeHorizon}; comparison off.`
        }
        whyItMatters="Keeps operational drift visible before it hits release checkpoints."
        nextAction={<Link to="/plan?tab=today">Review Today</Link>}
      />

      <WhatChangedThisWeek
        chart={chart}
        chartError={chartError}
        timeHorizon={timeHorizon}
        compareMode={compareMode}
        overviewDataLoading={overviewDataLoading}
      />
      <PortfolioHealth
        rows={portfolioRows}
        chart={chart}
        compareMode={compareMode}
        timeHorizon={timeHorizon}
        overviewDataLoading={overviewDataLoading}
      />
      <RiskOverview rows={portfolioRows} />
      <StandardsAndTraceability
        childrenList={Array.isArray(state.children) ? state.children : []}
        portfolioRows={portfolioRows}
      />
      <RecentWins wins={wins} />
      <DecisionBacklog hasChargeArtifact={hasCharge} />

      {websites.length > 0 && (
        <section className="le-cc-section" aria-labelledby="le-cc-sites">
          <h2 id="le-cc-sites" className="le-cc-section__title">
            Published sites
          </h2>
          <p className="le-cc-section__lead">
            Static or Firebase sites in this workspace —{' '}
            <Link className="le-cc-link" to="/websites">
              open Sites hub
            </Link>{' '}
            for browse previews.
          </p>
          <ul className="le-list">
            {websites.map((w) => (
              <li key={w.name}>
                <Link to={`/websites/browse/${encodeURIComponent(w.name)}`}>
                  <strong>{w.name}</strong>
                </Link>
                {w.html_total != null ? ` · ${w.html_total} HTML page(s)` : ''}
              </li>
            ))}
          </ul>
        </section>
      )}

      <TechnicalDetails summary="All workspace entries (directory view)">
        <p className="le-cc-section__lead">
          Full directory-style listing.{' '}
          <a href="/docs/index.html" target="_blank" rel="noreferrer">
            Workspace setup
          </a>
        </p>
        {sorted.length === 0 ? (
          <StatePanel
            variant="empty"
            density="compact"
            title="No workspace children in this scan"
            description="The scanner did not return child paths. Open a folder that contains your repositories, or adjust the workspace root and rescan."
            actions={
              <a className="le-btn le-btn--small" href="/docs/index.html" target="_blank" rel="noreferrer">
                Workspace setup (docs)
              </a>
            }
          />
        ) : (
          <WorkspaceAllEntriesTable sorted={sorted} />
        )}
      </TechnicalDetails>

      <TechnicalDetails summary="Technical details — raw workspace JSON">
        <p className="le-raw-hint">Full /api/workspace-state payload (debug).</p>
        <pre className="le-preview le-json">{JSON.stringify(state, null, 2)}</pre>
      </TechnicalDetails>
    </>
  )
}
