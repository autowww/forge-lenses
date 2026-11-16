import { useEffect, useMemo } from 'react'
import { FlowArtifactsOnboardingCallout } from '../components/onboarding/FlowArtifactsOnboardingCallout'
import { StudioFirstRunWizard } from '../components/onboarding/StudioFirstRunWizard'
import { recordPageFailure } from '../telemetry/studioTelemetry'
import { useWorkspace } from '../context/WorkspaceContext'
import { useOverviewTelemetry } from '../context/OverviewTelemetryContext'
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
  WorkspaceOperationalSnapshot,
  HomeLlmUsageBand,
  MondayChecklist,
} from '../components/home'
import { PortfolioAttentionStrip as PortfolioAttention } from '../components/home/PortfolioAttentionStrip'
import { StudioInAppTour } from '../components/onboarding/StudioInAppTour'
import { WorkspaceStateFallback } from '../components/WorkspaceStateFallback'
import {
  PageAiInsightCard,
  PageHeader,
  type PageHeaderStatusChip,
  PageSummaryBand,
  TechnicalDetails,
} from '../components/page'
import { STUDIO_VOCAB } from '../nav/studioVisibleCopy'
import { Link } from 'react-router-dom'
import { DocsHealthHomeBand } from '../components/docs-health/DocsHealthHomeBand'
import { DocsHealthSummary } from '../components/docs-health/DocsHealthSummary'
import { DocsManagementSummary } from '../components/doc-management/DocsManagementSummary'
import { WorkspaceSparseGuide } from '../components/onboarding/WorkspaceSparseGuide'
import { DocsHealthActiveRunsBand } from '../components/docs-health/DocsHealthActiveRunsBand'
import { StudioInlineAssist } from '../components/StudioInlineAssist'
import { chargeMdCandidates } from '../lib/copilotPageEvidence'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'

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
  const { timeHorizon, compareMode, overviewDataLoading } = useShellChrome()
  const { payload: chart, loading: overviewLoading, error: chartError } = useOverviewTelemetry()

  useEffect(() => {
    if (chartError) recordPageFailure('home_overview_charts', 'overview chart payload failed')
  }, [chartError])

  const portfolioRows = useMemo(
    () => buildRepoPortfolioRows(state, chart),
    [state, chart],
  )

  const wins = useMemo(() => pickRecentWins(portfolioRows, 5), [portfolioRows])

  if (!state) return <WorkspaceStateFallback />

  const websites = state.websites ?? []
  const hasCharge = anyChargeArtifact(state)

  const statusChips: PageHeaderStatusChip[] = []
  if (chartError) statusChips.push({ label: 'Charts unavailable', tone: 'warn' })
  else if (overviewDataLoading || overviewLoading) statusChips.push({ label: 'Loading charts…', tone: 'muted' })
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
          <Link className="le-btn le-btn--primary" to="/plan?tab=today">
            Open {STUDIO_VOCAB.today}
          </Link>
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

      <PortfolioAttention rows={portfolioRows} />

      <MondayChecklist rows={portfolioRows} />

      <StudioFirstRunWizard />

      <WorkspaceSparseGuide telemetryTag="home" />

      <StudioInAppTour />

      <DocsHealthSummary />

      <DocsManagementSummary />

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
        overviewDataLoading={overviewDataLoading || overviewLoading}
      />
      <PortfolioHealth
        rows={portfolioRows}
        chart={chart}
        compareMode={compareMode}
        timeHorizon={timeHorizon}
        overviewDataLoading={overviewDataLoading || overviewLoading}
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

      <TechnicalDetails summary="Technical details — raw workspace JSON">
        <p className="le-raw-hint">Full /api/workspace-state payload (debug).</p>
        <pre className="le-preview le-json">{JSON.stringify(state, null, 2)}</pre>
      </TechnicalDetails>
    </>
  )
}
