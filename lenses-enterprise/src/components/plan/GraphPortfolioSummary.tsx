import { Link } from 'react-router-dom'

/** Embedded in roadmaps-matrix and timeline-context when the orchestration graph is enabled. */
export type OrchestrationPortfolioOverlay = {
  schema_version?: number
  rollups?: {
    dependency_pressure_max?: number
    open_vulnerabilities?: number
    incidents_open_heuristic?: number
    graph_completeness?: { score?: number; story_count?: number }
    milestone_confidence_baseline?: number | null
    critical_path?: { ok?: boolean; length?: number; error?: string }
  }
  scenarios?: { id: string; display_name: string }[]
  depends_on_edges?: { from_id: string; to_id: string; from_kind: string; to_kind: string }[]
  workstreams?: {
    id: string
    display_name: string
    capacity_units?: number
    allocated_stories?: number
    utilization?: number | null
  }[]
  slip_impact_demo?: { if_entity_slips?: string; transitive_blocked?: string[] }
}

type Props = {
  overlay: OrchestrationPortfolioOverlay
  /** Opens Plan with two scenarios selected (query string). */
  planCompareHref?: string
  idPrefix?: string
}

const EDGE_PREVIEW = 14

/**
 * Read-only strip: portfolio rollups and dependency preview from the canonical graph
 * (matrix / timeline payloads).
 */
export function GraphPortfolioSummary({ overlay, planCompareHref, idPrefix = 'le-graph-port' }: Props) {
  const r = overlay.rollups
  const gc = r?.graph_completeness
  const cp = r?.critical_path
  const edges = overlay.depends_on_edges ?? []
  const slip = overlay.slip_impact_demo

  return (
    <section className="le-plan-section" aria-labelledby={`${idPrefix}-h`}>
      <h2 id={`${idPrefix}-h`} className="le-plan-section__title">
        Portfolio graph overlay
      </h2>
      <p className="le-plan-section__lead">
        Same canonical orchestration data that powers the plan cockpit: dependency pressure, readiness, and
        critical-path length. Milestone cells below include per-row graph hints when stories link to graph
        entities.
      </p>
      <div className="le-plan-readiness-grid">
        <div className="le-plan-card">
          <span className="le-plan-card__label">Dep. pressure (max in)</span>
          <span className="le-plan-card__value">{r?.dependency_pressure_max ?? '—'}</span>
        </div>
        <div className="le-plan-card">
          <span className="le-plan-card__label">Graph completeness</span>
          <span className="le-plan-card__value">
            {gc?.score != null ? `${gc.score}%` : '—'}
            {gc?.story_count != null ? ` (${gc.story_count} stories)` : ''}
          </span>
        </div>
        <div className="le-plan-card">
          <span className="le-plan-card__label">Milestone conf. (baseline)</span>
          <span className="le-plan-card__value">
            {r?.milestone_confidence_baseline != null ? r.milestone_confidence_baseline : '—'}
          </span>
        </div>
        <div className="le-plan-card">
          <span className="le-plan-card__label">Critical path (d)</span>
          <span className="le-plan-card__value">{cp?.ok ? cp.length : '—'}</span>
        </div>
        <div className="le-plan-card">
          <span className="le-plan-card__label">Open vulns / incidents</span>
          <span className="le-plan-card__value">
            {r?.open_vulnerabilities ?? '—'} / {r?.incidents_open_heuristic ?? '—'}
          </span>
        </div>
      </div>
      {planCompareHref ? (
        <p className="forge-support" style={{ marginTop: '0.75rem' }}>
          <Link className="le-btn le-btn--small" to={planCompareHref}>
            Open scenario comparison in Plan
          </Link>
        </p>
      ) : null}
      {slip?.if_entity_slips && (slip.transitive_blocked?.length ?? 0) > 0 ? (
        <p className="forge-support" style={{ marginTop: '0.5rem' }}>
          If <code>{slip.if_entity_slips}</code> slips, <strong>{slip.transitive_blocked!.length}</strong> items
          are transitively in the <code>depends_on</code> chain used for the slip preview (see Plan cockpit for
          the full list).
        </p>
      ) : null}
      {overlay.workstreams?.length ? (
        <div style={{ marginTop: '1rem' }}>
          <h3 className="le-plan-section__title" style={{ fontSize: '1rem' }}>
            Capacity placeholders (workstreams)
          </h3>
          <ul className="forge-support" style={{ margin: '0.25rem 0 0', paddingLeft: '1.25rem' }}>
            {overlay.workstreams.map((w) => (
              <li key={w.id}>
                <strong>{w.display_name}</strong> — {w.allocated_stories ?? 0} stories allocated
                {w.capacity_units != null && w.capacity_units > 0
                  ? ` · cap ${w.capacity_units}${w.utilization != null ? ` (${Math.round(w.utilization * 100)}% util.)` : ''}`
                  : ''}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {edges.length > 0 ? (
        <details className="le-raw-wrap" style={{ marginTop: '1rem' }}>
          <summary>
            <code>depends_on</code> edges ({edges.length}, showing {Math.min(EDGE_PREVIEW, edges.length)})
          </summary>
          <ul className="forge-support" style={{ margin: '0.5rem 0 0', paddingLeft: '1.25rem' }}>
            {edges.slice(0, EDGE_PREVIEW).map((e) => (
              <li key={`${e.from_id}-${e.to_id}`}>
                <code>{e.from_id}</code> ({e.from_kind || '?'}) depends on <code>{e.to_id}</code> (
                {e.to_kind || '?'})
              </li>
            ))}
          </ul>
        </details>
      ) : (
        <p className="forge-support" style={{ marginTop: '0.75rem' }}>
          No <code>depends_on</code> edges in the graph yet.
        </p>
      )}
    </section>
  )
}
