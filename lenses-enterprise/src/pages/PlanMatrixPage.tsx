import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useSearchParams } from 'react-router-dom'
import { apiGetJson } from '../api/http'
import {
  getOverviewChartPayload,
  perRepoLinesByKey,
  sparklinePeriodTotals,
  type OverviewChartPayload,
} from '../api/chartOverview'
import {
  GraphPortfolioSummary,
  NestedRoadmapWorkspaceFrame,
  PlanningClusterLocalNav,
  PlanningClusterPageHeader,
  type OrchestrationPortfolioOverlay,
} from '../components/plan'
import { DEMO_SCENARIO_BASELINE_ID, DEMO_SCENARIO_STRETCH_ID } from '../constants/demoOrchestration'
import { useWorkspace } from '../context/WorkspaceContext'
import { useNavigationMode } from '../nav/useNavigationMode'
import { getPlanningClusterPageIdentity } from '../nav/planningClusterPageIdentity'
import { STUDIO_GLOSSARY, STUDIO_VOCAB } from '../nav/studioVisibleCopy'
import { StatePanel } from '../components/page'
import { useShellChrome } from '../context/ShellChromeContext'
import { tierToClass } from '../lib/kpiTrendUi'
import { resolveUxFailure, type UxResolvedFailure } from '../lib/uxPageState'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'

type ByWbs = {
  story_count: number
  stories: { id: string; title: string; task_count: number }[]
}

type MatrixMilestone = {
  milestone_key: string
  epic_key: string
  title: string
  theme: string
  month_bucket: string
  wbs_loaded_count: number
  unique_story_count: number
  by_wbs: Record<string, ByWbs>
  orchestration?: {
    linked_story_count?: number
    max_dependency_pressure?: number
    slip_preview?: { for_entity_id?: string; transitive_blocked_count?: number }
  }
}

type RoadmapMatrixRow = {
  roadmap_rel: string
  repo_hint: string
  milestones: MatrixMilestone[]
  stats: { pairs_built: number; pairs_cap: number; truncated: boolean }
}

type RoadmapMatrixPayload = {
  ok: boolean
  error?: string
  repo_filter: string
  repo_options: string[]
  column_order: string[]
  roadmaps: RoadmapMatrixRow[]
  limits?: { max_roadmaps: number; max_spine_pairs: number; max_stories_per_wbs_cell: number }
  warnings?: string[]
  orchestration_portfolio?: OrchestrationPortfolioOverlay
}

function monthLabel(bucket: string): string {
  if (bucket === 'unscheduled') return 'Unscheduled'
  const m = bucket.match(/^(\d{4})-(\d{2})$/)
  if (!m) return bucket
  const d = new Date(Number(m[1]), Number(m[2]) - 1, 1)
  return d.toLocaleString(undefined, { month: 'short', year: 'numeric' })
}

function planStoryHref(
  repo: string,
  wbs: string,
  roadmap: string,
  storyId: string,
): string {
  const q = new URLSearchParams()
  if (repo) q.set('repo', repo)
  q.set('wbs_p', wbs)
  if (roadmap) q.set('roadmap_p', roadmap)
  q.set('id', storyId)
  q.set('tab', 'story')
  return `/plan?${q.toString()}`
}

export function PlanMatrixPage() {
  useLensesCopilotPage({ route: 'plan-matrix' })
  const { state } = useWorkspace()
  const { mode } = useNavigationMode()
  const { pathname, search: locationSearch } = useLocation()
  const pageIdentity = useMemo(
    () => getPlanningClusterPageIdentity(pathname, locationSearch, mode),
    [pathname, locationSearch, mode],
  )
  const [sp, setSp] = useSearchParams()
  const repoParam = (sp.get('repo') || '').trim() || 'all'
  const [payload, setPayload] = useState<RoadmapMatrixPayload | null>(null)
  const [chartPayload, setChartPayload] = useState<OverviewChartPayload | null>(null)
  const [err, setErr] = useState<UxResolvedFailure | null>(null)
  const [loading, setLoading] = useState(false)
  const { timeHorizon } = useShellChrome()

  const resolved = state?.resolved_at
  const linesByRepo = useMemo(() => perRepoLinesByKey(chartPayload), [chartPayload])

  const load = useCallback(async () => {
    setLoading(true)
    setErr(null)
    try {
      const q = repoParam === 'all' ? '' : `?repo=${encodeURIComponent(repoParam)}`
      const data = await apiGetJson<RoadmapMatrixPayload>(`/api/roadmaps-matrix${q}`)
      setPayload(data)
      if (!data.ok) {
        const raw = data.error || 'matrix_unavailable'
        setErr({
          kind: 'unavailable',
          title: 'Roadmap matrix unavailable',
          description:
            'The matrix service returned without data for this filter. Try another repository filter or confirm WBS and roadmap files are present.',
          technical: raw,
          fetchKind: 'unknown',
        })
      }
    } catch (e) {
      setPayload(null)
      setErr(resolveUxFailure(e))
    } finally {
      setLoading(false)
    }
  }, [repoParam])

  useEffect(() => {
    void load()
  }, [load, resolved])

  useEffect(() => {
    void getOverviewChartPayload(timeHorizon)
      .then(setChartPayload)
      .catch(() => setChartPayload(null))
  }, [timeHorizon, resolved])

  const columns = useMemo(() => {
    const order = payload?.column_order?.length
      ? payload.column_order
      : ['unscheduled']
    return order
  }, [payload])

  const [modal, setModal] = useState<{
    roadmap: RoadmapMatrixRow
    column: string
    milestones: MatrixMilestone[]
  } | null>(null)

  const milestonesForCell = useCallback(
    (rm: RoadmapMatrixRow, col: string) => {
      return (rm.milestones ?? []).filter((m) => {
        const mb = m.month_bucket || 'unscheduled'
        if (col === 'unscheduled') return mb === 'unscheduled'
        return mb === col
      })
    },
    [],
  )

  const planCompareHref = `/plan?scenario_a=${encodeURIComponent(DEMO_SCENARIO_BASELINE_ID)}&scenario_b=${encodeURIComponent(DEMO_SCENARIO_STRETCH_ID)}`

  const cellSummary = (ms: MatrixMilestone[]) => {
    let stories = 0
    const wbsPaths = new Set<string>()
    for (const m of ms) {
      stories += m.unique_story_count
      for (const w of Object.keys(m.by_wbs)) {
        wbsPaths.add(w)
      }
    }
    return { stories, wbs: wbsPaths.size, n: ms.length }
  }

  function healthTier(
    ms: MatrixMilestone[],
    repoHint: string,
  ): 'green' | 'amber' | 'red' | 'muted' {
    if (!ms.length) return 'muted'
    const pressure = Math.max(...ms.map((m) => m.orchestration?.max_dependency_pressure ?? 0))
    const blocked = ms.some((m) => (m.orchestration?.slip_preview?.transitive_blocked_count ?? 0) > 0)
    const thin = ms.every((m) => m.unique_story_count === 0)
    const kpiTier = linesByRepo.get(repoHint.trim().toLowerCase())?.tier
    if (blocked || pressure >= 8 || kpiTier === 'red') return 'red'
    if (thin || pressure >= 4 || kpiTier === 'amber') return 'amber'
    return 'green'
  }

  function repoSparkline(repoHint: string, ms: MatrixMilestone[]): number[] {
    const entry = linesByRepo.get(repoHint.trim().toLowerCase())
    if (entry?.period_totals?.length) {
      return sparklinePeriodTotals(entry.period_totals.map((x) => Number(x)))
    }
    return ms
      .slice(0, 6)
      .map((m) => Math.max(m.unique_story_count, m.wbs_loaded_count, 1))
  }

  return (
    <div className="le-roadmap-matrix-page">
      <PlanningClusterLocalNav />
      <PlanningClusterPageHeader identity={pageIdentity} headerClassName="le-plan-page-header">
        <p className="forge-support le-roadmap-matrix__intro">
          {STUDIO_GLOSSARY.roadmapMatrix.long} Milestones roll up from plan spines across each roadmap and every WBS
          in the same repository. Open a story in the {STUDIO_VOCAB.story} tab using the links below. Same backlog
          scope as {STUDIO_VOCAB.planSummary.toLowerCase()} travels in the URL when you use the bar above.
        </p>
      </PlanningClusterPageHeader>

      <section className="le-roadmap-matrix__horizon" aria-label="Roadmap horizon">
        <h2 className="le-plan-section__title">Roadmap horizon</h2>
        <p className="forge-support le-plan-section__lead">
          Interactive drill-down view for the scoped roadmap file (below the matrix table). Repository filter matches the
          matrix dropdown.
        </p>
        <NestedRoadmapWorkspaceFrame frameMinHeight="min(50vh, 28rem)" />
      </section>

      <div
        className={`le-roadmap-matrix__toolbar${loading ? ' le-roadmap-matrix__toolbar--loading' : ''}`}
      >
        {loading ? (
          <div className="le-roadmap-matrix__toolbar-blade le-loading-blade" aria-hidden />
        ) : null}
        <label className="le-roadmap-matrix__label" htmlFor="le-matrix-repo">
          Repository
        </label>
        <select
          id="le-matrix-repo"
          className="le-roadmap-matrix__select"
          value={repoParam}
          onChange={(e) => {
            const v = e.target.value
            const next = new URLSearchParams(sp)
            if (v === 'all') next.delete('repo')
            else next.set('repo', v)
            setSp(next, { replace: true })
          }}
          disabled={loading}
        >
          <option value="all">All repositories</option>
          {(payload?.repo_options ?? []).map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
        <button
          type="button"
          className="le-roadmap-matrix__refresh"
          onClick={() => void load()}
          disabled={loading}
        >
          Refresh
        </button>
        {payload?.warnings?.length ? (
          <span className="le-roadmap-matrix__warn" role="status">
            Partial results (pair cap).
          </span>
        ) : null}
      </div>

      {err ? (
        <StatePanel
          variant="error"
          density="compact"
          title={err.title}
          description={err.description}
          technicalDetail={err.technical}
          actions={
            <button type="button" className="le-btn le-btn--primary" onClick={() => void load()}>
              Retry
            </button>
          }
        />
      ) : null}

      {payload?.ok && payload.orchestration_portfolio ? (
        <GraphPortfolioSummary
          overlay={payload.orchestration_portfolio}
          planCompareHref={planCompareHref}
          idPrefix="le-matrix-portfolio"
        />
      ) : null}

      {!payload?.ok && !err ? (
        <div
          className="le-roadmap-matrix__loading-panel le-loading-blade"
          role="status"
          aria-live="polite"
        >
          <p className="forge-support le-roadmap-matrix__loading-text">Loading matrix…</p>
        </div>
      ) : null}

      {payload?.ok && payload.roadmaps.length === 0 ? (
        <div className="le-roadmap-matrix__emptyIllustration" role="status">
          <p className="forge-support">No roadmap / WBS pairs found for this filter.</p>
        </div>
      ) : null}

      {payload?.ok && payload.roadmaps.length > 0 ? (
        <div className="le-roadmap-matrix__scroll">
          <table className="le-roadmap-matrix le-roadmap-matrix--sticky">
            <thead className="le-roadmap-matrix__thead--sticky">
              <tr>
                <th scope="col" className="le-roadmap-matrix__th-roadmap">
                  Roadmap
                </th>
                {columns.map((c) => (
                  <th key={c} scope="col" className="le-roadmap-matrix__th-bucket">
                    {monthLabel(c)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {payload.roadmaps.map((rm) => (
                <tr key={rm.roadmap_rel}>
                  <th scope="row" className="le-roadmap-matrix__row-h">
                    <span className="le-roadmap-matrix__path" title={rm.roadmap_rel}>
                      {rm.roadmap_rel}
                    </span>
                    <span className="le-roadmap-matrix__repo">{rm.repo_hint}</span>
                    {rm.stats.truncated ? (
                      <span className="le-roadmap-matrix__trunc" title="Spine pair cap">
                        · truncated
                      </span>
                    ) : null}
                  </th>
                  {columns.map((col) => {
                    const ms = milestonesForCell(rm, col)
                    const { stories, wbs, n } = cellSummary(ms)
                    const empty = n === 0 || stories === 0
                    const tier = healthTier(ms, rm.repo_hint)
                    const spark = repoSparkline(rm.repo_hint, ms)
                    const kpiTierClass = tierToClass(linesByRepo.get(rm.repo_hint.trim().toLowerCase())?.tier)
                    const milestoneTitle =
                      n === 1 ? ms[0]?.title?.trim() || ms[0]?.milestone_key || '' : ''
                    const outcomeTitle =
                      n > 1
                        ? ms
                            .slice(0, 2)
                            .map((m) => m.title?.trim() || m.milestone_key)
                            .filter(Boolean)
                            .join(' · ')
                        : milestoneTitle
                    return (
                      <td key={col} className={`le-roadmap-matrix__cell le-roadmap-matrix__cell--${tier}`}>
                        {empty ? (
                          <span className="le-roadmap-matrix__empty">—</span>
                        ) : (
                          <button
                            type="button"
                            className="le-roadmap-matrix__cell-btn"
                            onClick={() => setModal({ roadmap: rm, column: col, milestones: ms })}
                          >
                            <span
                              className={`le-roadmap-matrix__healthTier le-roadmap-matrix__healthTier--${tier} ${kpiTierClass}`}
                              aria-hidden
                            />
                            {spark.length > 1 ? (
                              <span className="le-roadmap-matrix__milestoneSparkline" aria-hidden>
                                {spark.map((v, i) => (
                                  <span
                                    key={i}
                                    className="le-roadmap-matrix__spark"
                                    style={{ height: `${Math.min(100, 12 + v * 6)}%` }}
                                  />
                                ))}
                              </span>
                            ) : null}
                            {outcomeTitle ? (
                              <span className="le-roadmap-matrix__milestone-title milestoneTitle" title={outcomeTitle}>
                                {outcomeTitle}
                              </span>
                            ) : null}
                            <span className="le-roadmap-matrix__stat">
                              {stories} stories · {wbs} WBS
                            </span>
                            {n > 1 ? (
                              <span className="le-roadmap-matrix__meta">{n} milestones</span>
                            ) : null}
                          </button>
                        )}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {modal ? (
        <div
          className="le-roadmap-matrix__modal-backdrop"
          role="presentation"
          onClick={() => setModal(null)}
        >
          <div
            className="le-roadmap-matrix__modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="le-matrix-modal-title"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="le-roadmap-matrix__modal-head">
              <h2 id="le-matrix-modal-title" className="le-roadmap-matrix__modal-title">
                {monthLabel(modal.column)} — {modal.roadmap.roadmap_rel}
              </h2>
              <button
                type="button"
                className="le-roadmap-matrix__modal-close"
                onClick={() => setModal(null)}
                aria-label="Close"
              >
                ×
              </button>
            </div>
            <div className="le-roadmap-matrix__modal-body">
              {modal.milestones.map((ms) => (
                <section key={ms.milestone_key} className="le-roadmap-matrix__ms">
                  <h3 className="le-roadmap-matrix__ms-title">
                    {ms.epic_key ? `${ms.epic_key} · ` : ''}
                    {ms.title}
                  </h3>
                  <p className="le-roadmap-matrix__ms-meta">
                    {ms.unique_story_count} stories across {ms.wbs_loaded_count} WBS
                  </p>
                  {ms.orchestration ? (
                    <p className="le-roadmap-matrix__ms-meta le-roadmap-matrix__orch">
                      Graph: {ms.orchestration.linked_story_count ?? 0} linked stories · max dependency
                      pressure {ms.orchestration.max_dependency_pressure ?? 0}
                      {ms.orchestration.slip_preview?.transitive_blocked_count != null ? (
                        <>
                          {' '}
                          · slip preview chain size {ms.orchestration.slip_preview.transitive_blocked_count}
                        </>
                      ) : null}
                    </p>
                  ) : null}
                  {Object.entries(ms.by_wbs).map(([wbsRel, bw]) => (
                    <div key={wbsRel} className="le-roadmap-matrix__wbs-block">
                      <p className="le-roadmap-matrix__wbs-path">{wbsRel}</p>
                      <ul className="le-roadmap-matrix__story-list">
                        {bw.stories.map((st) => (
                          <li key={`${wbsRel}-${st.id}`}>
                            <Link
                              className="le-roadmap-matrix__story-link"
                              to={planStoryHref(
                                modal.roadmap.repo_hint,
                                wbsRel,
                                modal.roadmap.roadmap_rel,
                                st.id,
                              )}
                            >
                              <code>{st.id}</code>
                              {st.title ? ` · ${st.title}` : null}
                              {typeof st.task_count === 'number' ? (
                                <span className="le-roadmap-matrix__tasks">
                                  {' '}
                                  ({st.task_count} tasks)
                                </span>
                              ) : null}
                            </Link>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </section>
              ))}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}

