import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useLocation, useSearchParams } from 'react-router-dom'
import { apiGetJson, qs } from '../api/http'
import {
  GraphPortfolioSummary,
  NestedRoadmapWorkspaceFrame,
  PlanningClusterLocalNav,
  PlanningClusterPageHeader,
  RoadmapDateEditor,
  TimelineMetrics,
  type OrchestrationPortfolioOverlay,
  type RoadmapDateRow,
} from '../components/plan'
import { TechnicalDetails, canShowTechnicalDetails } from '../components/page'
import { TimelineGantt, type GanttBar } from '../components/plan/TimelineGantt'
import { DEMO_SCENARIO_BASELINE_ID, DEMO_SCENARIO_STRETCH_ID } from '../constants/demoOrchestration'
import { useNavigationMode } from '../nav/useNavigationMode'
import { getPlanningClusterPageIdentity } from '../nav/planningClusterPageIdentity'
import { useWorkspace } from '../context/WorkspaceContext'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'
import { wbsBacklogPickerLabel, roadmapLocationLabel, clusterHeadingLabel } from '../util/planScopeCluster'
import { friendlyRepoLabel } from '../util/planDisplayNames'
import {
  lastScopeFromParams,
  readPersistedScope,
  rememberScope,
} from '../lib/timelineScopeMemory'

type TimelineMetricsPayload = {
  horizon_counts?: Record<string, number>
  epic_bars?: { label: string; percent: number }[]
}

type TimelinePayload = {
  ok?: boolean
  selected?: { repo?: string; wbs_p?: string; roadmap_p?: string }
  gantt_html?: string
  gantt_milestones?: string[]
  gantt_bars?: GanttBar[]
  metrics?: TimelineMetricsPayload
  metrics_html?: string
  date_rows?: RoadmapDateRow[]
  editor_html?: string
  roadmap_source_href?: string
  repo_hints?: string[]
  wbs_options?: { rel_path: string; repo_hint: string }[]
  roadmap_options?: { rel_path: string; repo_hint: string }[]
  orchestration_portfolio?: OrchestrationPortfolioOverlay
}

export function TimelinePage() {
  useLensesCopilotPage({ route: 'timeline' })
  const { mode } = useNavigationMode()
  const { state } = useWorkspace()
  const { pathname, search: locationSearch } = useLocation()
  const pageIdentity = useMemo(
    () => getPlanningClusterPageIdentity(pathname, locationSearch, mode),
    [pathname, locationSearch, mode],
  )
  const [sp, setSp] = useSearchParams()
  const repo = sp.get('repo') || ''
  const wbsP = sp.get('wbs_p') || ''
  const roadmapP = sp.get('roadmap_p') || ''
  const [data, setData] = useState<TimelinePayload | null>(null)
  const restoredScopeRef = useRef(false)

  useEffect(() => {
    if (restoredScopeRef.current) return
    if (repo || wbsP || roadmapP) {
      restoredScopeRef.current = true
      return
    }
    const lastScope = readPersistedScope()
    if (!lastScope) {
      restoredScopeRef.current = true
      return
    }
    restoredScopeRef.current = true
    const next = new URLSearchParams(sp)
    if (lastScope.repo) next.set('repo', lastScope.repo)
    if (lastScope.wbs_p) next.set('wbs_p', lastScope.wbs_p)
    if (lastScope.roadmap_p) next.set('roadmap_p', lastScope.roadmap_p)
    setSp(next, { replace: true })
  }, [repo, wbsP, roadmapP, setSp, sp])

  const reloadTimeline = useCallback(() => {
    const q = qs({
      repo: repo || undefined,
      wbs_p: wbsP || undefined,
      roadmap_p: roadmapP || undefined,
    })
    void apiGetJson<TimelinePayload>(`/api/timeline-context${q}`)
      .then(setData)
      .catch(() => setData(null))
  }, [repo, wbsP, roadmapP])

  useEffect(() => {
    const persistedScope = lastScopeFromParams(repo, wbsP, roadmapP)
    if (persistedScope.repo || persistedScope.wbs_p || persistedScope.roadmap_p) {
      rememberScope(persistedScope)
    }
  }, [repo, wbsP, roadmapP])

  useEffect(() => {
    reloadTimeline()
  }, [reloadTimeline])

  function setField(key: string, value: string) {
    const next = new URLSearchParams(sp)
    if (value) next.set(key, value)
    else next.delete(key)
    setSp(next)
  }

  const planCompareHref = `/plan?scenario_a=${encodeURIComponent(DEMO_SCENARIO_BASELINE_ID)}&scenario_b=${encodeURIComponent(DEMO_SCENARIO_STRETCH_ID)}`

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

  const legacyGanttMarkup = data?.gantt_html
  const roadmapRel = data?.selected?.roadmap_p ?? roadmapP

  return (
    <>
      <PlanningClusterLocalNav />
      <PlanningClusterPageHeader
        identity={pageIdentity}
        freshness={scanFreshness}
        purpose="Gantt, metrics, and roadmap editor for the scope you pick below — same backlog context as Plan summary."
      >
        <TechnicalDetails summary="How this view fits Studio" defaultOpen={false}>
          <p className="forge-support">
            Timeline uses structured React components for metrics and date editing, backed by{' '}
            <code className="le-mono">GET /api/timeline-context</code>.
          </p>
        </TechnicalDetails>
        <TechnicalDetails summary="Technical — timeline API" defaultOpen={false}>
          <p className="forge-support" style={{ margin: 0 }}>
            Payload includes <code className="le-mono">date_rows</code>, structured <code className="le-mono">metrics</code>, and Gantt bars.
          </p>
        </TechnicalDetails>
      </PlanningClusterPageHeader>
      {data?.orchestration_portfolio ? (
        <GraphPortfolioSummary
          overlay={data.orchestration_portfolio}
          planCompareHref={planCompareHref}
          idPrefix="le-timeline-portfolio"
        />
      ) : null}
      <section className="le-timeline-roadmap-horizon" aria-label="Roadmap horizon">
        <h2 className="le-plan-section__title">Roadmap horizon</h2>
        <p className="forge-support le-plan-section__lead">
          Drill-down roadmap for the scope you select below — same fields as the timeline context.
        </p>
        <NestedRoadmapWorkspaceFrame frameMinHeight="min(48vh, 26rem)" />
      </section>
      <div className="le-form-row" style={{ flexDirection: 'column', alignItems: 'stretch' }}>
        <label>
          Repository
          <select
            className="le-select"
            value={repo}
            onChange={(e) => setField('repo', e.target.value)}
          >
            <option value="">—</option>
            {(data?.repo_hints ?? []).map((h) => (
              <option key={h} value={h}>
                {friendlyRepoLabel(h) || clusterHeadingLabel(h)}
              </option>
            ))}
          </select>
        </label>
        <label>
          WBS
          <select
            className="le-select"
            value={wbsP}
            onChange={(e) => setField('wbs_p', e.target.value)}
          >
            <option value="">—</option>
            {(data?.wbs_options ?? []).map((w) => (
              <option key={w.rel_path} value={w.rel_path} title={w.rel_path}>
                {wbsBacklogPickerLabel(w.rel_path, w.repo_hint)}
              </option>
            ))}
          </select>
        </label>
        <label>
          Roadmap
          <select
            className="le-select"
            value={roadmapP}
            onChange={(e) => setField('roadmap_p', e.target.value)}
          >
            <option value="">—</option>
            {(data?.roadmap_options ?? []).map((r) => (
              <option key={r.rel_path} value={r.rel_path} title={r.rel_path}>
                {roadmapLocationLabel(r.rel_path, r.repo_hint)}
              </option>
            ))}
          </select>
        </label>
      </div>
      {data?.roadmap_source_href && (
        <p>
          <a href={data.roadmap_source_href}>Roadmap source</a>
        </p>
      )}
      {data?.gantt_bars?.length ? (
        <TimelineGantt milestones={data.gantt_milestones ?? []} bars={data.gantt_bars} />
      ) : null}
      {canShowTechnicalDetails() && legacyGanttMarkup ? (
        <div
          className="le-panel lenses-timeline-gantt lenses-timeline-gantt--legacy"
          dangerouslySetInnerHTML={{ __html: legacyGanttMarkup }}
        />
      ) : null}
      <TimelineMetrics metrics={data?.metrics} />
      {canShowTechnicalDetails() && data?.metrics_html ? (
        <div dangerouslySetInnerHTML={{ __html: data.metrics_html }} />
      ) : null}
      <RoadmapDateEditor
        relPath={roadmapRel}
        rows={(data?.date_rows ?? []) as RoadmapDateRow[]}
        onSaved={reloadTimeline}
      />
      {canShowTechnicalDetails() && data?.editor_html ? (
        <div className="le-panel mt-3" dangerouslySetInnerHTML={{ __html: data.editor_html }} />
      ) : null}
      <TechnicalDetails summary="Raw timeline payload (debug)" defaultOpen={false}>
        <pre className="le-preview le-json">{JSON.stringify(data, null, 2)}</pre>
      </TechnicalDetails>
    </>
  )
}
