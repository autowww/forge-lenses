import { useMemo } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { qs } from '../../api/http'
import { readFeatureDisabled } from '../../lib/apiInternalFields'
import { useResilientJsonBlock } from '../../hooks/useResilientJsonBlock'
import { DataResilienceBar, StatePanel } from '../page'

type PortfolioCtx = {
  ok?: boolean
  scenario_compare?: {
    ok?: boolean
    a?: { display_name?: string; id?: string; payload?: Record<string, unknown> }
    b?: { display_name?: string; id?: string; payload?: Record<string, unknown> }
    delta_numeric?: Record<string, number>
  }
  scenarios?: { id?: string; display_name?: string; summary?: string }[]
}

function num(v: unknown): string {
  if (typeof v === 'number' && Number.isFinite(v)) return String(v)
  return '—'
}

export function ScenarioTradeoffs() {
  const [sp] = useSearchParams()
  const scenarioA = (sp.get('scenario_a') || '').trim()
  const scenarioB = (sp.get('scenario_b') || '').trim()

  const apiPath = useMemo(() => {
    if (!scenarioA || !scenarioB) return null
    return `/api/orchestration/portfolio-context${qs({
      scenario_a: scenarioA,
      scenario_b: scenarioB,
    })}`
  }, [scenarioA, scenarioB])

  const block = useResilientJsonBlock<PortfolioCtx>(apiPath, {
    snapshotKey: `portfolio-scenarios:${scenarioA}:${scenarioB}`,
  })

  if (!scenarioA || !scenarioB) {
    return (
      <section className="le-plan-section" aria-labelledby="le-plan-scenario-h">
        <h2 id="le-plan-scenario-h" className="le-plan-section__title">
          Scenario tradeoffs
        </h2>
        <p className="le-plan-section__lead">
          Select two scenarios above (Portfolio planning panel) to compare scope, dates, and risk signals from the
          orchestration graph.
        </p>
        <p className="le-plan-section__empty">
          Set <code className="le-mono">scenario_a</code> and <code className="le-mono">scenario_b</code> query params,
          or use <strong>Load demo comparison</strong> in the portfolio panel.
        </p>
      </section>
    )
  }

  if (block.phase === 'loading' && !block.data) {
    return (
      <section className="le-plan-section" aria-labelledby="le-plan-scenario-h">
        <h2 id="le-plan-scenario-h" className="le-plan-section__title">
          Scenario tradeoffs
        </h2>
        <StatePanel variant="loading" title="Loading scenario comparison" description="Portfolio context API." />
      </section>
    )
  }

  if (block.phase === 'error' && block.failure) {
    return (
      <section className="le-plan-section" aria-labelledby="le-plan-scenario-h">
        <h2 id="le-plan-scenario-h" className="le-plan-section__title">
          Scenario tradeoffs
        </h2>
        <DataResilienceBar
          variant="error"
          failure={block.failure}
          snapshotAtMs={null}
          snapshotTimeLabel={null}
          snapshotAgeLabel={null}
          onRetry={block.retry}
        />
      </section>
    )
  }

  const data = block.data
  if (readFeatureDisabled(data)) {
    return (
      <section className="le-plan-section" aria-labelledby="le-plan-scenario-h">
        <h2 id="le-plan-scenario-h" className="le-plan-section__title">
          Scenario tradeoffs
        </h2>
        <p className="le-plan-section__lead">
          Orchestration graph is off. Enable <code className="le-mono">LENSES_EXPERIMENTAL_ORCHESTRATION_GRAPH</code> and
          seed the graph to compare scenarios.
        </p>
      </section>
    )
  }

  const cmp = data?.scenario_compare
  if (!cmp?.ok || !cmp.a || !cmp.b) {
    return (
      <section className="le-plan-section" aria-labelledby="le-plan-scenario-h">
        <h2 id="le-plan-scenario-h" className="le-plan-section__title">
          Scenario tradeoffs
        </h2>
        <p className="le-plan-section__lead">
          No comparison returned for these scenario ids. Confirm ids match entities in{' '}
          <Link to="/plan/matrix">Roadmap matrix</Link> or the demo graph.
        </p>
        <p className="forge-support">
          Requested: <code className="le-mono">{scenarioA}</code> vs <code className="le-mono">{scenarioB}</code>
        </p>
      </section>
    )
  }

  const d = cmp.delta_numeric || {}

  return (
    <section className="le-plan-section" aria-labelledby="le-plan-scenario-h">
      <h2 id="le-plan-scenario-h" className="le-plan-section__title">
        Scenario tradeoffs
      </h2>
      <p className="le-plan-section__lead">
        Side-by-side view from <code className="le-mono">/api/orchestration/portfolio-context</code> (live graph data).
      </p>
      <div className="le-panel" style={{ marginBottom: '0.75rem' }}>
        <h3 className="le-panel__title" style={{ fontSize: '0.95rem' }}>
          {cmp.a.display_name ?? cmp.a.id}
        </h3>
        <ul className="le-list forge-support" style={{ fontSize: '0.88rem' }}>
          <li>Horizon shift (days): {num((cmp.a.payload as { horizon_shift_days?: number })?.horizon_shift_days)}</li>
          <li>Capacity scale: {num((cmp.a.payload as { capacity_scale?: number })?.capacity_scale)}</li>
          <li>Milestone confidence: {num((cmp.a.payload as { milestone_confidence?: number })?.milestone_confidence)}</li>
          <li>Risk score: {num((cmp.a.payload as { risk_score?: number })?.risk_score)}</li>
        </ul>
      </div>
      <div className="le-panel" style={{ marginBottom: '0.75rem' }}>
        <h3 className="le-panel__title" style={{ fontSize: '0.95rem' }}>
          {cmp.b.display_name ?? cmp.b.id}
        </h3>
        <ul className="le-list forge-support" style={{ fontSize: '0.88rem' }}>
          <li>Horizon shift (days): {num((cmp.b.payload as { horizon_shift_days?: number })?.horizon_shift_days)}</li>
          <li>Capacity scale: {num((cmp.b.payload as { capacity_scale?: number })?.capacity_scale)}</li>
          <li>Milestone confidence: {num((cmp.b.payload as { milestone_confidence?: number })?.milestone_confidence)}</li>
          <li>Risk score: {num((cmp.b.payload as { risk_score?: number })?.risk_score)}</li>
        </ul>
      </div>
      <div className="le-panel">
        <h3 className="le-panel__title" style={{ fontSize: '0.95rem' }}>
          Deltas (B − A)
        </h3>
        <ul className="le-list forge-support" style={{ fontSize: '0.88rem' }}>
          {Object.keys(d).length === 0 ? (
            <li>No numeric deltas in response.</li>
          ) : (
            Object.entries(d).map(([k, v]) => (
              <li key={k}>
                <strong>{k}</strong>: {num(v)}
              </li>
            ))
          )}
        </ul>
      </div>
    </section>
  )
}
