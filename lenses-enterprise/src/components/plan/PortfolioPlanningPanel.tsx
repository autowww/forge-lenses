import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiGetJson } from '../../api/http'
import { readFeatureDisabled } from '../../lib/apiInternalFields'
import { StatePanel } from '../page/StatePanel'
import { DEMO_ORCHESTRATION_STORY_ID } from '../../constants/demoOrchestration'

type ScenarioRow = { id: string; display_name: string; payload?: Record<string, unknown> }

type PortfolioContext = {
  ok?: boolean
  rollups?: {
    dependency_pressure_max?: number
    open_vulnerabilities?: number
    graph_completeness?: { score?: number; story_count?: number }
    milestone_confidence_baseline?: number | null
    critical_path?: { ok?: boolean; length?: number; path?: string[]; error?: string }
  }
  scenarios?: ScenarioRow[]
  scenario_compare?: {
    ok?: boolean
    a?: { display_name?: string; payload?: Record<string, unknown> }
    b?: { display_name?: string; payload?: Record<string, unknown> }
    delta_numeric?: Record<string, number | null | undefined>
  }
  slip_impact?: { focus_entity_id?: string; transitive_blocked?: string[] }
  workstreams?: { id: string; display_name: string; capacity_units: number; allocated_stories: number }[]
  depends_on_edges?: { from_id: string; to_id: string; from_kind: string; to_kind: string }[]
}

type Props = {
  scenarioA: string
  scenarioB: string
  onScenarioA: (v: string) => void
  onScenarioB: (v: string) => void
  onLoadDemoComparison?: () => void
}

/**
 * Sprint 2 — scenario comparison, rollups, slip preview, dependencies (canonical graph).
 */
export function PortfolioPlanningPanel({
  scenarioA,
  scenarioB,
  onScenarioA,
  onScenarioB,
  onLoadDemoComparison,
}: Props) {
  const [data, setData] = useState<PortfolioContext | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const q = useMemo(() => {
    const p = new URLSearchParams()
    if (scenarioA.trim()) p.set('scenario_a', scenarioA.trim())
    if (scenarioB.trim()) p.set('scenario_b', scenarioB.trim())
    p.set('slip_focus', DEMO_ORCHESTRATION_STORY_ID)
    return `?${p.toString()}`
  }, [scenarioA, scenarioB])

  const load = useCallback(async () => {
    setLoading(true)
    setErr(null)
    try {
      const j = await apiGetJson<PortfolioContext>(`/api/orchestration/portfolio-context${q}`)
      setData(j)
      if (readFeatureDisabled(j)) return
      if (j.ok === false && !readFeatureDisabled(j)) setErr('Portfolio context unavailable')
    } catch (e) {
      setData(null)
      setErr(e instanceof Error ? e.message : 'Request failed')
    } finally {
      setLoading(false)
    }
  }, [q])

  useEffect(() => {
    void load()
  }, [load])

  const scenarios = data?.scenarios ?? []
  const cmp = data?.scenario_compare

  return (
    <section className="le-plan-section" aria-labelledby="le-portfolio-planning-h">
      <h2 id="le-portfolio-planning-h" className="le-plan-section__title">
        Portfolio alignment and scenarios
      </h2>
      <p className="le-plan-section__lead">
        Rollups and comparisons use the{' '}
        <Link to="/" title="Workspace home">
          canonical orchestration graph
        </Link>{' '}
        (objectives through delivery). Pick two scenarios to compare scope, dates, and confidence signals (see Scenario
        tradeoffs below).
      </p>

      {loading ? <p className="forge-support">Loading portfolio context…</p> : null}
      {err ? (
        <StatePanel
          variant="error"
          density="compact"
          title="Portfolio context failed"
          description={err}
          actions={
            <button type="button" className="le-btn le-btn--primary le-btn--small" onClick={() => void load()}>
              Retry
            </button>
          }
        />
      ) : null}

      {readFeatureDisabled(data) ? (
        <StatePanel
          variant="empty"
          density="compact"
          title="Orchestration graph disabled"
          description="Enable LENSES_EXPERIMENTAL_ORCHESTRATION_GRAPH on the server to load portfolio planning data."
        />
      ) : null}

      {data && !readFeatureDisabled(data) && data.ok ? (
        <>
          <div className="le-form-row" style={{ flexWrap: 'wrap', gap: '0.75rem', marginBottom: '1rem' }}>
            <label>
              Scenario A{' '}
              <select
                className="le-select"
                value={scenarioA}
                onChange={(e) => onScenarioA(e.target.value)}
              >
                <option value="">—</option>
                {scenarios.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.display_name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Scenario B{' '}
              <select
                className="le-select"
                value={scenarioB}
                onChange={(e) => onScenarioB(e.target.value)}
              >
                <option value="">—</option>
                {scenarios.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.display_name}
                  </option>
                ))}
              </select>
            </label>
            {onLoadDemoComparison ? (
              <button type="button" className="le-btn le-btn--small" onClick={onLoadDemoComparison}>
                Load demo: Baseline vs Stretch
              </button>
            ) : null}
          </div>

          {cmp?.ok && cmp.a && cmp.b ? (
            <div className="le-panel forge-card" style={{ marginBottom: '1rem' }}>
              <h3 className="le-h3" style={{ fontSize: '1rem', marginTop: 0 }}>
                Scenario comparison
              </h3>
              <table className="le-cc-table">
                <thead>
                  <tr>
                    <th scope="col">Field</th>
                    <th scope="col">{cmp.a.display_name ?? 'A'}</th>
                    <th scope="col">{cmp.b.display_name ?? 'B'}</th>
                    <th scope="col">Δ (B − A)</th>
                  </tr>
                </thead>
                <tbody>
                  {(['horizon_shift_days', 'capacity_scale', 'risk_score', 'milestone_confidence'] as const).map(
                    (k) => (
                      <tr key={k}>
                        <td>
                          <code className="le-mono">{k}</code>
                        </td>
                        <td>{String((cmp.a?.payload ?? {})[k] ?? '—')}</td>
                        <td>{String((cmp.b?.payload ?? {})[k] ?? '—')}</td>
                        <td>{cmp.delta_numeric?.[k] != null ? String(cmp.delta_numeric[k]) : '—'}</td>
                      </tr>
                    ),
                  )}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="forge-support">
              Select two scenarios above to compare horizon shift, capacity scale, risk score, and milestone
              confidence (demo seed includes Baseline vs Stretch).
            </p>
          )}

          <div className="le-plan-cards">
            <div className="le-plan-card">
              <span className="le-plan-card__label">Graph completeness</span>
              <span className="le-plan-card__value">
                {data.rollups?.graph_completeness?.score != null
                  ? `${data.rollups.graph_completeness.score}%`
                  : '—'}
              </span>
            </div>
            <div className="le-plan-card">
              <span className="le-plan-card__label">Dependency pressure (max)</span>
              <span className="le-plan-card__value">
                {data.rollups?.dependency_pressure_max ?? '—'}
              </span>
            </div>
            <div className="le-plan-card">
              <span className="le-plan-card__label">Open vulnerabilities</span>
              <span className="le-plan-card__value">{data.rollups?.open_vulnerabilities ?? '—'}</span>
            </div>
            <div className="le-plan-card">
              <span className="le-plan-card__label">Critical path length (days)</span>
              <span className="le-plan-card__value">
                {data.rollups?.critical_path?.ok ? data.rollups.critical_path.length : '—'}
              </span>
            </div>
          </div>

          {data.slip_impact?.transitive_blocked?.length ? (
            <div className="forge-card le-panel mt-3" style={{ marginTop: '1rem' }}>
              <h3 className="le-h3" style={{ fontSize: '1rem', marginTop: 0 }}>
                What slips if this slips (demo)
              </h3>
              <p className="forge-support">
                If <code className="le-mono">{data.slip_impact.focus_entity_id}</code> slips, these items are
                transitively blocked by <code className="le-mono">depends_on</code>:
              </p>
              <ul className="le-list">
                {data.slip_impact.transitive_blocked.map((id) => (
                  <li key={id}>
                    <code className="le-mono">{id}</code>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {data.workstreams?.length ? (
            <div className="forge-card le-panel mt-3" style={{ marginTop: '1rem' }}>
              <h3 className="le-h3" style={{ fontSize: '1rem', marginTop: 0 }}>
                Capacity placeholders (workstreams)
              </h3>
              <ul className="le-list">
                {data.workstreams.map((w) => (
                  <li key={w.id}>
                    <strong>{w.display_name}</strong> — capacity {w.capacity_units}, allocated stories{' '}
                    {w.allocated_stories}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {data.depends_on_edges?.length ? (
            <details className="le-raw-wrap mt-3">
              <summary>Cross-product dependencies ({data.depends_on_edges.length})</summary>
              <ul className="le-list forge-support">
                {data.depends_on_edges.map((e) => (
                  <li key={`${e.from_id}-${e.to_id}`}>
                    <code className="le-mono">{e.from_id}</code> ({e.from_kind}) depends on{' '}
                    <code className="le-mono">{e.to_id}</code> ({e.to_kind})
                  </li>
                ))}
              </ul>
            </details>
          ) : (
            <p className="forge-support mt-2">No depends_on edges in the current graph.</p>
          )}
        </>
      ) : null}
    </section>
  )
}
