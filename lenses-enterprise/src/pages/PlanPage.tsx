import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useSearchParams } from 'react-router-dom'
import { apiGetJson, qs } from '../api/http'
import { useWorkspace } from '../context/WorkspaceContext'
import { useNavigationMode } from '../nav/useNavigationMode'
import { getPlanningClusterPageIdentity } from '../nav/planningClusterPageIdentity'
import {
  PlanningClusterLocalNav,
  PlanningClusterPageHeader,
  PlanScopeBar,
  PlanReadiness,
  PortfolioPlanningPanel,
  OutcomeAlignment,
  ScenarioTradeoffs,
  type PlanOrchestrationSummary,
  MilestoneMap,
  NestedRoadmapWorkspaceFrame,
  WbsCoverage,
  RoadmapTrace,
  DecisionsWaiting,
  SourceContext,
  StoryDetailModal,
  StoryHubPanel,
  EpicHubPanel,
  SpecFlowBoard,
  CeremonyBridgePanel,
  HandoffLoopPanel,
  OutcomeLoopPanel,
} from '../components/plan'
import {
  computeOutcomeAlignment,
  computePlanReadiness,
  getMilestones,
} from '../lib/planMetrics'
import {
  TodayChargeView,
  WhatChangedSincePrior,
  CommitmentsAtRisk,
  BlockersNeedingAction,
  CrossProjectDependencies,
  ExecutionBoardLinks,
  PipelineTraceabilityCard,
  QualityGatesCard,
  DevSecOpsCard,
  RepoWorkflowOpsCard,
  DeliveryControlTowerCard,
  ReleaseManagerCard,
  OpsDeliveryCard,
  DecisionsNeededToday,
  TodayActionBand,
  FreshnessChip,
} from '../components/delivery'
import { DocsHealthWorkBand } from '../components/docs-health/DocsHealthWorkBand'
import {
  DEMO_ORCHESTRATION_STORY_ID,
  DEMO_SCENARIO_BASELINE_ID,
  DEMO_SCENARIO_STRETCH_ID,
} from '../constants/demoOrchestration'
import { chargeMdCandidates } from '../lib/copilotPageEvidence'
import { friendlyDocumentTitle } from '../util/planDisplayNames'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'
import { StatePanel, TechnicalDetails } from '../components/page'
import {
  PLAN_PAGE_COPY,
  PLAN_TAB_LABEL,
  STUDIO_VOCAB,
  WORK_COPILOT_DEFAULT_PLAN,
  WORK_COPILOT_DEFAULT_TODAY,
  WORK_COPILOT_DEFAULT_SPEC_BOARD,
} from '../nav/studioVisibleCopy'

function PlanApiErrorPanel({ message }: { message: string }) {
  return (
    <StatePanel
      variant="error"
      title="Plan data could not be loaded"
      description="We couldn’t load the plan or delivery view for this scope. Check your WBS and roadmap picks, confirm Lenses finished its workspace scan, then reload or open Plan with a clean scope."
      technicalDetail={message}
      aiRecovery={{
        prompt:
          'Plan / work view in Lenses failed to load. What should I verify (WBS path, roadmap, repo scope) and what is the next step?',
        label: 'Ask Chat how to recover plan scope',
      }}
      actions={
        <>
          <button type="button" className="le-btn le-btn--primary" onClick={() => window.location.reload()}>
            Reload page
          </button>
          <Link className="le-btn" to="/plan">
            Open plan (reset query)
          </Link>
        </>
      }
    />
  )
}

type Milestone = {
  epic_key?: string
  title?: string
  theme?: string
  stories?: { id: string; title?: string; task_count?: number }[]
}

export function PlanPage() {
  const { mode } = useNavigationMode()
  const { pathname, search: locationSearch } = useLocation()
  const { state } = useWorkspace()
  const [sp, setSp] = useSearchParams()

  const pageIdentity = useMemo(
    () => getPlanningClusterPageIdentity(pathname, locationSearch, mode),
    [pathname, locationSearch, mode],
  )

  const repo = sp.get('repo') || ''
  const wbsP = sp.get('wbs_p') || ''
  const roadmapP = sp.get('roadmap_p') || ''
  const nodeId = sp.get('id') || ''
  const tab = sp.get('tab') || 'plan'

  /** When Work journey selects Sources, scroll the Sources block into view (Flow has it above the sub-tabs; Artifacts mounts it in the source tab). */
  useEffect(() => {
    if (tab !== 'source') return
    const t = window.setTimeout(() => {
      document.getElementById('le-plan-source-h')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }, 0)
    return () => clearTimeout(t)
  }, [tab, pathname, mode])

  const copilotDefaultQuery = useMemo(() => {
    if (mode === 'flow' && tab === 'today') return WORK_COPILOT_DEFAULT_TODAY
    if (tab === 'spec-board') return WORK_COPILOT_DEFAULT_SPEC_BOARD
    if (mode === 'flow') return WORK_COPILOT_DEFAULT_PLAN
    return undefined
  }, [mode, tab])

  const copilotEvidence = useMemo(() => {
    const r = repo.trim()
    const nid = nodeId.trim()
    const bits = ['Forge Studio · Plan']
    if (r) bits.push(`repo ${r}`)
    if (nid) bits.push(`focus entity ${nid}`)
    const w = wbsP.trim()
    if (w) bits.push(`wbs ${w}`)
    const rm = roadmapP.trim()
    if (rm) bits.push(`roadmap ${rm}`)
    return {
      pageContextSummary: bits.join(' · '),
      relatedMdRelPaths: chargeMdCandidates(r || undefined),
    }
  }, [repo, nodeId, wbsP, roadmapP])

  useLensesCopilotPage({
    route: 'plan',
    projectSlug: repo.trim() || undefined,
    entityId: nodeId.trim() || undefined,
    scopeSite: repo.trim() || undefined,
    defaultQuery: copilotDefaultQuery,
    pageContextSummary: copilotEvidence.pageContextSummary,
    relatedMdRelPaths: copilotEvidence.relatedMdRelPaths,
  })

  const [spine, setSpine] = useState<Record<string, unknown> | null>(null)
  const [workModel, setWorkModel] = useState<Record<string, unknown> | null>(null)
  const [today, setToday] = useState<Record<string, unknown> | null>(null)
  const [specBoard, setSpecBoard] = useState<Record<string, unknown> | null>(null)
  const [epicHub, setEpicHub] = useState<Record<string, unknown> | null>(null)
  const [specBoardLoading, setSpecBoardLoading] = useState(false)
  const [story, setStory] = useState<Record<string, unknown> | null>(null)
  const [storyLoading, setStoryLoading] = useState(false)
  const [storyModalOpen, setStoryModalOpen] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [loadSpine, setLoadSpine] = useState(false)

  const wbsList = useMemo(() => state?.wbs ?? [], [state])
  const rmList = useMemo(() => state?.roadmaps ?? [], [state])

  const setFields = useCallback(
    (patch: Record<string, string | undefined>) => {
      const next = new URLSearchParams(sp)
      for (const [k, v] of Object.entries(patch)) {
        if (v === undefined || v === '') next.delete(k)
        else next.set(k, v)
      }
      setSp(next)
    },
    [sp, setSp],
  )

  useEffect(() => {
    if (!wbsP.trim()) {
      /* eslint-disable react-hooks/set-state-in-effect -- clear plan state when WBS scope empty */
      setSpine(null)
      setWorkModel(null)
      setToday(null)
      /* eslint-enable react-hooks/set-state-in-effect */
      return
    }
    setErr(null)
    setLoadSpine(true)
    const q = qs({
      wbs_p: wbsP,
      repo: repo || undefined,
      roadmap_p: roadmapP || undefined,
    })
    apiGetJson<Record<string, unknown>>(`/api/plan-spine${q}`)
      .then(setSpine)
      .catch((e) => setErr(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoadSpine(false))
  }, [wbsP, repo, roadmapP])

  useEffect(() => {
    if (!wbsP.trim()) {
      /* eslint-disable-next-line react-hooks/set-state-in-effect -- clear work model when scope empty */
      setWorkModel(null)
      return
    }
    const q = qs({
      wbs_p: wbsP,
      repo: repo || undefined,
      roadmap_p: roadmapP || undefined,
      ...(nodeId ? { node_id: nodeId } : {}),
    })
    apiGetJson<Record<string, unknown>>(`/api/forge-work-model${q}`)
      .then(setWorkModel)
      .catch(() => setWorkModel(null))
  }, [wbsP, repo, roadmapP, nodeId])

  useEffect(() => {
    if (!wbsP.trim()) {
      /* eslint-disable-next-line react-hooks/set-state-in-effect -- clear today payload when scope empty */
      setToday(null)
      return
    }
    const needToday = tab === 'today' || mode === 'flow'
    if (!needToday) {
      setToday(null)
      return
    }
    const q = qs({
      wbs_p: wbsP,
      repo: repo || undefined,
      roadmap_p: roadmapP || undefined,
    })
    apiGetJson<Record<string, unknown>>(`/api/today-charge${q}`)
      .then(setToday)
      .catch(() => setToday(null))
  }, [wbsP, repo, roadmapP, tab, mode])

  const epicProfile = specBoard?.profile === 'epic'

  useEffect(() => {
    if (!wbsP.trim()) {
      setSpecBoard(null)
      return
    }
    setSpecBoardLoading(true)
    const q = qs({
      wbs_p: wbsP,
      repo: repo || undefined,
      roadmap_p: roadmapP || undefined,
    })
    apiGetJson<Record<string, unknown>>(`/api/epic-spec-board${q}`)
      .then(setSpecBoard)
      .catch(() => setSpecBoard(null))
      .finally(() => setSpecBoardLoading(false))
  }, [wbsP, repo, roadmapP])

  useEffect(() => {
    if (!wbsP.trim() || !nodeId.trim() || tab !== 'spec-board') {
      setEpicHub(null)
      return
    }
    if (!/^M\d+E\d+$/i.test(nodeId.trim())) {
      setEpicHub(null)
      return
    }
    const q = qs({
      id: nodeId,
      wbs_p: wbsP,
      repo: repo || undefined,
      roadmap_p: roadmapP || undefined,
    })
    apiGetJson<Record<string, unknown>>(`/api/epic-hub${q}`)
      .then(setEpicHub)
      .catch(() => setEpicHub(null))
  }, [nodeId, wbsP, repo, roadmapP, tab])

  const refetchSpecBoard = useCallback(() => {
    if (!wbsP.trim()) return
    const q = qs({
      wbs_p: wbsP,
      repo: repo || undefined,
      roadmap_p: roadmapP || undefined,
    })
    apiGetJson<Record<string, unknown>>(`/api/epic-spec-board${q}`)
      .then(setSpecBoard)
      .catch(() => setSpecBoard(null))
  }, [wbsP, repo, roadmapP])

  const refetchEpicHub = useCallback(() => {
    if (!wbsP.trim() || !nodeId.trim() || !/^M\d+E\d+$/i.test(nodeId.trim())) return
    const q = qs({
      id: nodeId,
      wbs_p: wbsP,
      repo: repo || undefined,
      roadmap_p: roadmapP || undefined,
    })
    apiGetJson<Record<string, unknown>>(`/api/epic-hub${q}`)
      .then(setEpicHub)
      .catch(() => setEpicHub(null))
  }, [nodeId, wbsP, repo, roadmapP])

  useEffect(() => {
    if (!wbsP.trim() || !nodeId.trim()) {
      /* eslint-disable react-hooks/set-state-in-effect -- clear story when scope or id missing */
      setStory(null)
      setStoryLoading(false)
      /* eslint-enable react-hooks/set-state-in-effect */
      return
    }
    setStoryLoading(true)
    const q = qs({
      id: nodeId,
      wbs_p: wbsP,
      repo: repo || undefined,
      roadmap_p: roadmapP || undefined,
    })
    apiGetJson<Record<string, unknown>>(`/api/story-hub${q}`)
      .then(setStory)
      .catch(() => setStory(null))
      .finally(() => setStoryLoading(false))
  }, [nodeId, wbsP, repo, roadmapP])

  const planTree = spine?.plan as { milestones?: Milestone[] } | undefined
  const milestonesLegacy = planTree?.milestones ?? []
  const milestones = getMilestones(spine)

  const focusStoryTitle = useMemo(() => {
    for (const ms of milestones) {
      for (const st of ms.stories ?? []) {
        if (st.id === nodeId) return st.title
      }
    }
    return undefined
  }, [milestones, nodeId])

  const openStoryModal = useCallback(
    (id: string) => {
      setFields({ id })
      setStoryModalOpen(true)
    },
    [setFields],
  )

  const closeStoryModal = useCallback(() => setStoryModalOpen(false), [])

  const openFullStoryTab = useCallback(() => {
    setStoryModalOpen(false)
    setFields({ tab: 'story' })
  }, [setFields])

  const tabs = epicProfile
    ? (['plan', 'today', 'spec-board', 'source'] as const)
    : (['plan', 'today', 'source'] as const)
  const showStoryTab = Boolean(nodeId.trim())

  const roadmapSummaryHref = roadmapP.trim()
    ? `/roadmaps/summary?${new URLSearchParams({ p: roadmapP }).toString()}`
    : null

  const scanFreshness =
    state?.resolved_at != null ? (
      <>
        Last scan:{' '}
        <time dateTime={state.resolved_at}>
          {new Date(state.resolved_at).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })}
        </time>
      </>
    ) : (
      'Last scan: not recorded'
    )

  const readiness = computePlanReadiness(wbsP, spine, workModel, err, roadmapP)
  const orchestrationSummary = (spine?.orchestration ?? null) as PlanOrchestrationSummary | null
  const alignment = computeOutcomeAlignment(spine, workModel)

  const storyModalEl = (
    <StoryDetailModal
      open={storyModalOpen}
      onClose={closeStoryModal}
      nodeId={nodeId}
      story={story}
      loading={Boolean(storyModalOpen && storyLoading)}
      onOpenFullStoryTab={openFullStoryTab}
    />
  )

  if (mode === 'flow') {
    const isFlowDelivery = tab === 'today'

    if (isFlowDelivery) {
      return (
        <>
          {storyModalEl}
          <PlanningClusterPageHeader
            identity={pageIdentity}
            freshness={
              <>
                {scanFreshness}
                {' · '}
                <FreshnessChip
                  resolvedAt={state?.resolved_at}
                  scopeComplete={Boolean(wbsP.trim())}
                />
              </>
            }
          >
            {wbsP.trim() ? (
              <p className="le-plan-page-header__context">
                <span className="le-plan-page-header__context-label">Backlog</span>{' '}
                <strong>{friendlyDocumentTitle(wbsP)}</strong>
                {roadmapP.trim() ? (
                  <>
                    {' '}
                    <span className="le-muted">·</span> {STUDIO_VOCAB.roadmap}{' '}
                    <strong>{friendlyDocumentTitle(roadmapP)}</strong>
                  </>
                ) : null}
              </p>
            ) : null}
            {repo.trim() ? (
              <TechnicalDetails summary="Repository shortcuts">
                <p className="forge-support" style={{ margin: 0 }}>
                  <Link className="le-btn le-btn--small" to={`/projects/${encodeURIComponent(repo.trim())}`}>
                    Open code workflow &amp; PR health for this repository
                  </Link>
                </p>
              </TechnicalDetails>
            ) : null}
          </PlanningClusterPageHeader>
          <PlanningClusterLocalNav />
          <TodayActionBand repoHint={repo} wbsSelected={Boolean(wbsP.trim())} />
          {err ? <PlanApiErrorPanel message={err} /> : null}

          <PlanScopeBar
            repo={repo}
            wbsP={wbsP}
            roadmapP={roadmapP}
            nodeId={nodeId}
            wbsList={wbsList}
            rmList={rmList}
            setFields={setFields}
            focusStoryTitle={focusStoryTitle}
            defaultScopeOpen={false}
          />

          <CommitmentsAtRisk payload={today} />
          <BlockersNeedingAction payload={today} />
          <DecisionsNeededToday payload={today} wbsSelected={Boolean(wbsP.trim())} />
          <ExecutionBoardLinks repoHint={repo} />
          <PipelineTraceabilityCard />
          <QualityGatesCard />
          <DevSecOpsCard />
          <RepoWorkflowOpsCard />
          <DeliveryControlTowerCard />
          <ReleaseManagerCard />
          <OpsDeliveryCard />
          <WhatChangedSincePrior />
          <CrossProjectDependencies />

          <TechnicalDetails summary="Demo orchestration trace (optional)" defaultOpen={false}>
            <HandoffLoopPanel workItemId={DEMO_ORCHESTRATION_STORY_ID} traceQueryStoryId={DEMO_ORCHESTRATION_STORY_ID} />
            <OutcomeLoopPanel workItemId={DEMO_ORCHESTRATION_STORY_ID} traceQueryStoryId={DEMO_ORCHESTRATION_STORY_ID} />
          </TechnicalDetails>

          <section className="le-delivery-section" aria-labelledby="le-delivery-evidence-h">
            <h2 id="le-delivery-evidence-h" className="le-delivery-section__title">
              Today charge &amp; evidence
            </h2>
            {today ? (
              <>
                <TodayChargeView payload={today} />
                <TechnicalDetails summary="Raw today JSON (debug)">
                  <pre className="le-preview le-json">{JSON.stringify(today, null, 2)}</pre>
                </TechnicalDetails>
              </>
            ) : wbsP.trim() ? (
              <p className="forge-support">Loading today…</p>
            ) : (
              <p className="le-delivery-section__empty">Select a WBS scope to load today-charge.</p>
            )}
          </section>

          <TechnicalDetails summary={`${STUDIO_VOCAB.planSummary}, milestones, and readiness`}>
            <p className="forge-support">
              Roadmap structure, readiness signals, milestones, and tradeoffs stay on the Plan tab — same backlog scope
              as this Today view.
            </p>
            <button type="button" className="le-btn le-btn--primary" onClick={() => setFields({ tab: 'plan' })}>
              Open {STUDIO_VOCAB.planSummary}
            </button>
          </TechnicalDetails>
        </>
      )
    }

    return (
      <>
        {storyModalEl}
        <PlanningClusterPageHeader
          identity={pageIdentity}
          freshness={
            <>
              {scanFreshness}
              {' · '}
              <FreshnessChip resolvedAt={state?.resolved_at} scopeComplete={Boolean(wbsP.trim())} />
            </>
          }
        >
          {wbsP.trim() ? (
            <p className="le-plan-page-header__context">
              <span className="le-plan-page-header__context-label">Backlog</span>{' '}
              <strong>{friendlyDocumentTitle(wbsP)}</strong>
              {roadmapP.trim() ? (
                <>
                  {' '}
                  <span className="le-muted">·</span> {STUDIO_VOCAB.roadmap}{' '}
                  <strong>{friendlyDocumentTitle(roadmapP)}</strong>
                </>
              ) : null}
            </p>
          ) : null}
          {repo.trim() ? (
            <TechnicalDetails summary="Repository shortcuts">
              <p className="forge-support" style={{ margin: 0 }}>
                <Link className="le-btn le-btn--small" to={`/projects/${encodeURIComponent(repo.trim())}`}>
                  Open code workflow &amp; PR health for this repository
                </Link>
              </p>
            </TechnicalDetails>
          ) : null}
        </PlanningClusterPageHeader>
        <PlanningClusterLocalNav />
        {err ? <PlanApiErrorPanel message={err} /> : null}

        <PlanScopeBar
          repo={repo}
          wbsP={wbsP}
          roadmapP={roadmapP}
          nodeId={nodeId}
          wbsList={wbsList}
          rmList={rmList}
          setFields={setFields}
          focusStoryTitle={focusStoryTitle}
          defaultScopeOpen={false}
        />

        {!wbsP.trim() && tab === 'plan' ? (
          <StatePanel
            variant="not_configured"
            density="compact"
            title="Pick a work backlog to load this plan"
            description="Use the scope tiles above first. Roadmap, milestones, and readiness fill in after you choose a backlog (and optionally a roadmap)."
            assistShortcuts={{ context: 'Plan summary' }}
            actions={
              <button
                type="button"
                className="le-btn le-btn--primary"
                onClick={() => document.getElementById('le-plan-scope-anchor')?.scrollIntoView({ behavior: 'smooth' })}
              >
                Jump to scope
              </button>
            }
          />
        ) : null}

        <PortfolioPlanningPanel
          scenarioA={sp.get('scenario_a') || ''}
          scenarioB={sp.get('scenario_b') || ''}
          onScenarioA={(v) => setFields({ scenario_a: v.trim() ? v : undefined })}
          onScenarioB={(v) => setFields({ scenario_b: v.trim() ? v : undefined })}
          onLoadDemoComparison={() =>
            setFields({
              scenario_a: DEMO_SCENARIO_BASELINE_ID,
              scenario_b: DEMO_SCENARIO_STRETCH_ID,
            })
          }
        />

        <PlanReadiness
          metrics={readiness}
          loadSpine={loadSpine}
          orchestration={orchestrationSummary}
        />
        <CeremonyBridgePanel studioPlanHref={`/plan?${sp.toString()}`} />
        <TechnicalDetails summary="Demo orchestration trace (optional)" defaultOpen={false}>
          <HandoffLoopPanel workItemId={DEMO_ORCHESTRATION_STORY_ID} traceQueryStoryId={DEMO_ORCHESTRATION_STORY_ID} />
          <OutcomeLoopPanel workItemId={DEMO_ORCHESTRATION_STORY_ID} traceQueryStoryId={DEMO_ORCHESTRATION_STORY_ID} />
        </TechnicalDetails>
        <OutcomeAlignment alignment={alignment} />
        <ScenarioTradeoffs />
        <MilestoneMap milestones={milestones} onOpenStoryDetails={openStoryModal} />
        <section className="le-plan-roadmap-horizon" aria-label="Roadmap horizon">
          <h2 className="le-plan-section__title">Roadmap horizon</h2>
          <p className="forge-support le-plan-section__lead">
            Same workspace matrix as the roadmap grid: month buckets and milestones for the repository and roadmap you
            set in the scope bar. Drill into a bar when WBS roll-up is available.
          </p>
          <NestedRoadmapWorkspaceFrame frameMinHeight="min(48vh, 26rem)" />
        </section>
        <WbsCoverage
          workModel={workModel}
          milestones={milestones}
          onSelectRoot={(rid) => setFields({ id: rid, tab: 'plan' })}
        />
        <RoadmapTrace roadmapP={roadmapP} roadmapSummaryHref={roadmapSummaryHref} />
        <DecisionsWaiting
          today={today}
          wbsSelected={Boolean(wbsP.trim())}
          onOpenTodayTab={() => setFields({ tab: 'today' })}
        />
        <SourceContext />

        <TechnicalDetails summary="Plan tab tools (Today charge, sources, story hub)" defaultOpen={false}>
        <section className="le-plan-secondary" aria-label="Plan tools">
          <h2 className="le-plan-section__title">{PLAN_PAGE_COPY.planDetailSectionTitle}</h2>
          <p className="le-plan-section__lead">{PLAN_PAGE_COPY.planDetailSectionLead}</p>
          <div className="le-form-row le-plan-tab-row">
            {tabs.map((t) => (
              <button
                key={t}
                type="button"
                className={`le-btn${tab === t ? ' le-btn--primary' : ''}`}
                onClick={() => setFields({ tab: t })}
              >
                {PLAN_TAB_LABEL[t]}
              </button>
            ))}
            {showStoryTab && (
              <button
                type="button"
                className={`le-btn${tab === 'story' ? ' le-btn--primary' : ''}`}
                onClick={() => setFields({ tab: 'story' })}
              >
                {PLAN_TAB_LABEL.story}
              </button>
            )}
          </div>

          {tab === 'plan' && (
            <>
              {loadSpine && <p className="forge-support">Loading plan spine…</p>}
              {!loadSpine && spine && milestonesLegacy.length === 0 && (
                <p className="le-plan-section__empty">No milestones in spine — see readiness above.</p>
              )}
              {workModel && (
                <section className="le-panel">
                  <h3 className="le-panel__title">Work graph (compact)</h3>
                  <p className="forge-support">
                    {(workModel.root_ids as string[] | undefined)?.length ?? 0} root node(s),{' '}
                    {Object.keys((workModel.nodes as object) ?? {}).length} total nodes.
                  </p>
                </section>
              )}
              <details className="le-raw-wrap">
                <summary>Raw plan / work model JSON</summary>
                <pre className="le-preview le-json">{JSON.stringify({ spine, workModel }, null, 2)}</pre>
              </details>
            </>
          )}

          {tab === 'today' && (
            <>
              <DocsHealthWorkBand />
              {today ? (
                <>
                  <TodayChargeView payload={today} />
                  <CeremonyBridgePanel studioPlanHref={`/plan?${sp.toString()}`} />
                  <HandoffLoopPanel workItemId={DEMO_ORCHESTRATION_STORY_ID} traceQueryStoryId={DEMO_ORCHESTRATION_STORY_ID} />
                  <OutcomeLoopPanel workItemId={DEMO_ORCHESTRATION_STORY_ID} traceQueryStoryId={DEMO_ORCHESTRATION_STORY_ID} />
                  <details className="le-raw-wrap">
                    <summary>Raw today JSON</summary>
                    <pre className="le-preview le-json">{JSON.stringify(today, null, 2)}</pre>
                  </details>
                </>
              ) : wbsP.trim() ? (
                <p className="forge-support">Loading today…</p>
              ) : null}
            </>
          )}

          {tab === 'source' && (
            <p className="forge-support" role="status">
              {STUDIO_VOCAB.sources} is summarized in the section above this strip — the page scrolls to that heading
              when you open this tab.
            </p>
          )}

          {tab === 'story' && !nodeId.trim() && (
            <StatePanel
              variant="empty"
              density="compact"
              title="Choose a work item"
              description="Pick a backlog in the scope tiles, then set a work item id, or open a story from the milestone map below when milestones are visible."
              assistShortcuts={{ context: 'Plan story tab' }}
            />
          )}
          {tab === 'story' && nodeId && story && (
            <>
              <StoryHubPanel story={story} nodeId={nodeId} />
              <TechnicalDetails summary="Raw story-hub JSON (debug)">
                <pre className="le-preview le-json">{JSON.stringify(story, null, 2)}</pre>
              </TechnicalDetails>
            </>
          )}
          {tab === 'story' && nodeId && !story && <p className="forge-support">Loading story hub…</p>}
        </section>
        </TechnicalDetails>
      </>
    )
  }

  /* Artifacts lens: legacy form-first layout */
  return (
    <>
      {storyModalEl}
      <PlanningClusterPageHeader
        identity={pageIdentity}
        freshness={
          <>
            {scanFreshness}
            {' · '}
            <FreshnessChip resolvedAt={state?.resolved_at} scopeComplete={Boolean(wbsP.trim())} />
          </>
        }
      >
        <TechnicalDetails summary="Artifacts lens">
          <p className="forge-support">{PLAN_PAGE_COPY.artifactsLensHint}</p>
        </TechnicalDetails>
      </PlanningClusterPageHeader>
      <PlanningClusterLocalNav />
      {err ? <PlanApiErrorPanel message={err} /> : null}
      <div className="le-form-row" style={{ flexDirection: 'column', alignItems: 'stretch' }}>
        <label>
          Repository hint{' '}
          <input
            className="le-input"
            value={repo}
            onChange={(e) => setFields({ repo: e.target.value })}
            style={{ width: '100%', maxWidth: '28rem' }}
          />
        </label>
        <label>
          WBS file{' '}
          <select
            className="le-select"
            value={wbsP}
            onChange={(e) => setFields({ wbs_p: e.target.value, id: undefined })}
          >
            <option value="">— choose —</option>
            {wbsList.map((w) => (
              <option key={w.rel_path} value={w.rel_path}>
                {w.rel_path} ({w.repo_hint})
              </option>
            ))}
          </select>
        </label>
        <label>
          Roadmap (optional){' '}
          <select
            className="le-select"
            value={roadmapP}
            onChange={(e) => setFields({ roadmap_p: e.target.value })}
          >
            <option value="">—</option>
            {rmList.map((r) => (
              <option key={r.rel_path} value={r.rel_path}>
                {r.rel_path}
              </option>
            ))}
          </select>
        </label>
        <label>
          Work item id{' '}
          <input
            className="le-input"
            value={nodeId}
            onChange={(e) => setFields({ id: e.target.value })}
            placeholder="WBS id (story hub)"
          />
        </label>
        <div className="le-form-row">
          {tabs.map((t) => (
            <button
              key={t}
              type="button"
              className={`le-btn${tab === t ? ' le-btn--primary' : ''}`}
              onClick={() => setFields({ tab: t })}
            >
              {PLAN_TAB_LABEL[t]}
            </button>
          ))}
          {showStoryTab && (
            <button
              type="button"
              className={`le-btn${tab === 'story' ? ' le-btn--primary' : ''}`}
              onClick={() => setFields({ tab: 'story' })}
            >
              {PLAN_TAB_LABEL.story}
            </button>
          )}
        </div>
      </div>

      {tab === 'plan' && (
        <>
          <PortfolioPlanningPanel
            scenarioA={sp.get('scenario_a') || ''}
            scenarioB={sp.get('scenario_b') || ''}
            onScenarioA={(v) => setFields({ scenario_a: v.trim() ? v : undefined })}
            onScenarioB={(v) => setFields({ scenario_b: v.trim() ? v : undefined })}
            onLoadDemoComparison={() =>
              setFields({
                scenario_a: DEMO_SCENARIO_BASELINE_ID,
                scenario_b: DEMO_SCENARIO_STRETCH_ID,
              })
            }
          />
          <PlanReadiness
            metrics={readiness}
            loadSpine={loadSpine}
            orchestration={orchestrationSummary}
          />
          <CeremonyBridgePanel studioPlanHref={`/plan?${sp.toString()}`} />
          <HandoffLoopPanel workItemId={DEMO_ORCHESTRATION_STORY_ID} traceQueryStoryId={DEMO_ORCHESTRATION_STORY_ID} />
          <OutcomeLoopPanel workItemId={DEMO_ORCHESTRATION_STORY_ID} traceQueryStoryId={DEMO_ORCHESTRATION_STORY_ID} />
          {loadSpine && <p className="forge-support">Loading plan spine…</p>}
          {!loadSpine && spine && milestonesLegacy.length > 0 && (
            <section className="le-panel">
              <h2 className="le-panel__title">Plan tree (from WBS)</h2>
              {milestonesLegacy.map((ms) => (
                <div key={String(ms.title)} style={{ marginBottom: '1.25rem' }}>
                  <h3 className="le-panel__title" style={{ fontSize: '1rem' }}>
                    {ms.title ?? ms.epic_key}
                    {ms.theme ? (
                      <span className="le-muted" style={{ fontWeight: 400 }}>
                        {' '}
                        — {ms.theme}
                      </span>
                    ) : null}
                  </h3>
                  <ul className="le-list" style={{ listStyle: 'none', paddingLeft: 0 }}>
                    {(ms.stories ?? []).map((st) => (
                      <li key={st.id} className="le-card" style={{ marginBottom: '0.35rem' }}>
                        <button
                          type="button"
                          className="le-btn"
                          style={{ marginRight: '0.5rem' }}
                          onClick={() => openStoryModal(st.id)}
                        >
                          View story
                        </button>
                        <strong>{st.id}</strong> — {st.title ?? '—'}
                        {st.task_count != null ? (
                          <span className="le-muted"> ({st.task_count} tasks)</span>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </section>
          )}
          {workModel && (
            <section className="le-panel">
              <h2 className="le-panel__title">Work model</h2>
              <p className="forge-support">
                {(workModel.root_ids as string[] | undefined)?.length ?? 0} root node(s),{' '}
                {Object.keys((workModel.nodes as object) ?? {}).length} total nodes.
              </p>
              <ul className="le-list" style={{ fontSize: '0.85rem' }}>
                {((workModel.root_ids as string[] | undefined) ?? []).map((rid) => (
                  <li key={rid}>
                    <button
                      type="button"
                      className="le-btn"
                      style={{ fontSize: '0.75rem', padding: '0.2rem 0.5rem' }}
                      onClick={() => setFields({ id: rid, tab: 'plan' })}
                    >
                      {rid}
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          )}
          <details className="le-raw-wrap">
            <summary>Raw plan / work model JSON</summary>
            <pre className="le-preview le-json">{JSON.stringify({ spine, workModel }, null, 2)}</pre>
          </details>
        </>
      )}

      {tab === 'today' && today && (
        <>
          <TodayChargeView payload={today} />
          <CeremonyBridgePanel studioPlanHref={`/plan?${sp.toString()}`} />
          <HandoffLoopPanel workItemId={DEMO_ORCHESTRATION_STORY_ID} traceQueryStoryId={DEMO_ORCHESTRATION_STORY_ID} />
          <OutcomeLoopPanel workItemId={DEMO_ORCHESTRATION_STORY_ID} traceQueryStoryId={DEMO_ORCHESTRATION_STORY_ID} />
          <details className="le-raw-wrap">
            <summary>Raw today JSON</summary>
            <pre className="le-preview le-json">{JSON.stringify(today, null, 2)}</pre>
          </details>
        </>
      )}

      {tab === 'spec-board' && epicProfile && specBoard && (
        <>
          <SpecFlowBoard
            columns={(specBoard.columns as { id: string; label: string }[]) ?? []}
            cards={(specBoard.cards as import('../components/plan/SpecFlowBoard').SpecFlowCard[]) ?? []}
            wbsP={wbsP}
            repo={repo}
            selectedId={nodeId.trim() || undefined}
            onSelect={(id) => setFields({ id, tab: 'spec-board' })}
            onTransitionComplete={refetchSpecBoard}
          />
          {nodeId.trim() && epicHub?.ok ? (
            <EpicHubPanel
              hub={epicHub}
              epicId={nodeId.trim()}
              wbsP={wbsP}
              repo={repo}
              onRefreshComplete={() => {
                refetchEpicHub()
                refetchSpecBoard()
              }}
            />
          ) : null}
          {specBoardLoading ? <p className="forge-support">Refreshing board…</p> : null}
        </>
      )}

      {tab === 'spec-board' && !epicProfile && !specBoardLoading && (
        <p className="forge-support">
          Spec Flow board is available under the Epic execution profile (Active Epics on Charge or forge-sdlc
          OpenSpec schema).
        </p>
      )}

      {tab === 'source' && (
        <>
          <SourceContext />
          <section className="le-plan-roadmap-horizon" aria-label="Roadmap horizon">
            <h2 className="le-plan-section__title">Roadmap horizon</h2>
            <p className="forge-support le-plan-section__lead">
              Same workspace matrix as the plan summary: month buckets and milestones for the scope you set above.
            </p>
            <NestedRoadmapWorkspaceFrame frameMinHeight="min(48vh, 26rem)" />
          </section>
          <RoadmapTrace roadmapP={roadmapP} roadmapSummaryHref={roadmapSummaryHref} />
        </>
      )}

      {tab === 'story' && !nodeId.trim() && (
        <p className="forge-support">Enter a work item id above, or select a story from the Plan tab.</p>
      )}
      {tab === 'story' && nodeId && story && (
        <>
          <StoryHubPanel story={story} nodeId={nodeId} />
          <details className="le-raw-wrap">
            <summary>Raw story-hub JSON</summary>
            <pre className="le-preview le-json">{JSON.stringify(story, null, 2)}</pre>
          </details>
        </>
      )}
      {tab === 'story' && nodeId && !story && <p className="forge-support">Loading story hub…</p>}
    </>
  )
}
