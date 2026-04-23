import { useEffect, useMemo, useRef, useState } from 'react'
import { useLocation, useSearchParams } from 'react-router-dom'
import { apiGetJson, qs } from '../api/http'
import {
  GraphPortfolioSummary,
  NestedRoadmapWorkspaceFrame,
  PlanningClusterLocalNav,
  PlanningClusterPageHeader,
  type OrchestrationPortfolioOverlay,
} from '../components/plan'
import { TechnicalDetails } from '../components/page'
import { DEMO_SCENARIO_BASELINE_ID, DEMO_SCENARIO_STRETCH_ID } from '../constants/demoOrchestration'
import { useNavigationMode } from '../nav/useNavigationMode'
import { getPlanningClusterPageIdentity } from '../nav/planningClusterPageIdentity'
import { FULL_WORKSPACE_UI, STUDIO_VOCAB } from '../nav/studioVisibleCopy'
import { useWorkspace } from '../context/WorkspaceContext'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'

type TimelinePayload = {
  ok?: boolean
  selected?: { repo?: string; wbs_p?: string; roadmap_p?: string }
  gantt_html?: string
  metrics_html?: string
  editor_html?: string
  roadmap_source_href?: string
  repo_hints?: string[]
  wbs_options?: { rel_path: string; repo_hint: string }[]
  roadmap_options?: { rel_path: string; repo_hint: string }[]
  orchestration_portfolio?: OrchestrationPortfolioOverlay
}

declare global {
  interface Window {
    ForgeRoadmapDates?: { init: (root?: ParentNode | null) => void }
  }
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
  const editorHostRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    const q = qs({
      repo: repo || undefined,
      wbs_p: wbsP || undefined,
      roadmap_p: roadmapP || undefined,
    })
    apiGetJson<TimelinePayload>(`/api/timeline-context${q}`)
      .then(setData)
      .catch(() => setData(null))
  }, [repo, wbsP, roadmapP])

  useEffect(() => {
    const el = editorHostRef.current
    if (!el || !data?.editor_html?.trim()) return

    function runInit() {
      window.ForgeRoadmapDates?.init(el)
    }

    if (document.querySelector('script[data-forge-roadmap-dates-js]')) {
      runInit()
      return
    }
    const s = document.createElement('script')
    s.src = '/__ks/js/roadmap-dates.js'
    s.async = true
    s.dataset.forgeRoadmapDatesJs = '1'
    s.onload = runInit
    document.body.appendChild(s)
  }, [data?.editor_html])

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
            This page uses HTML fragments from the workspace timeline service. For the legacy full three-pane roadmap
            UI, open{' '}
            <a href="/timeline" title={FULL_WORKSPACE_UI.navHint}>
              full workspace {STUDIO_VOCAB.timeline}
            </a>
            .
          </p>
        </TechnicalDetails>
        <TechnicalDetails summary="Technical — timeline API" defaultOpen={false}>
          <p className="forge-support" style={{ margin: 0 }}>
            Payload from <code className="le-mono">GET /api/timeline-context</code> (Gantt + metrics HTML + editor host).
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
                {h}
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
              <option key={w.rel_path} value={w.rel_path}>
                {w.rel_path}
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
              <option key={r.rel_path} value={r.rel_path}>
                {r.rel_path}
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
      {data?.gantt_html && (
        <div
          className="le-panel lenses-timeline-gantt"
          dangerouslySetInnerHTML={{ __html: data.gantt_html }}
        />
      )}
      {data?.metrics_html && (
        <div dangerouslySetInnerHTML={{ __html: data.metrics_html }} />
      )}
      {data?.editor_html && (
        <div
          ref={editorHostRef}
          className="le-panel mt-3"
          dangerouslySetInnerHTML={{ __html: data.editor_html }}
        />
      )}
      <TechnicalDetails summary="Raw timeline payload (debug)" defaultOpen={false}>
        <pre className="le-preview le-json">{JSON.stringify(data, null, 2)}</pre>
      </TechnicalDetails>
    </>
  )
}
