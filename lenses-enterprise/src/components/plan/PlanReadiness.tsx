import type { PlanReadinessMetrics } from '../../lib/planMetrics'

export type PlanOrchestrationSummary = {
  graph_completeness_score?: number
  dependency_pressure_max?: number
  critical_path?: { ok?: boolean; length?: number; error?: string }
}

type Props = {
  metrics: PlanReadinessMetrics
  loadSpine: boolean
  /** From plan-spine ``orchestration`` (canonical graph completeness vs heuristics-only). */
  orchestration?: PlanOrchestrationSummary | null
}

export function PlanReadiness({ metrics, loadSpine, orchestration }: Props) {
  const { wbsSelected, spineLoaded, spineError, milestoneCount, nodeCount, rootCount, roadmapLinked } =
    metrics

  return (
    <section className="le-plan-section" aria-labelledby="le-plan-readiness-h">
      <h2 id="le-plan-readiness-h" className="le-plan-section__title">
        Plan readiness
      </h2>
      <p className="le-plan-section__lead">
        Snapshot from plan spine and work model, plus graph-backed completeness when the orchestration DB is
        available. Use the <strong>Plan</strong> tab raw JSON section for full API payloads once a WBS is
        selected.
      </p>
      {spineError && <p className="le-danger">{spineError}</p>}
      {loadSpine && <p className="forge-support">Loading plan spine…</p>}
      <div className="le-plan-cards">
        <div className="le-plan-card">
          <span className="le-plan-card__label">WBS selected</span>
          <span className="le-plan-card__value">{wbsSelected ? 'Yes' : 'No'}</span>
        </div>
        <div className="le-plan-card">
          <span className="le-plan-card__label">Spine loaded</span>
          <span className="le-plan-card__value">{spineLoaded ? 'Yes' : 'No'}</span>
        </div>
        <div className="le-plan-card">
          <span className="le-plan-card__label">Milestones</span>
          <span className="le-plan-card__value">{milestoneCount}</span>
        </div>
        <div className="le-plan-card">
          <span className="le-plan-card__label">Work nodes</span>
          <span className="le-plan-card__value">{nodeCount}</span>
        </div>
        <div className="le-plan-card">
          <span className="le-plan-card__label">Root nodes</span>
          <span className="le-plan-card__value">{rootCount}</span>
        </div>
        <div className="le-plan-card">
          <span className="le-plan-card__label">Roadmap linked</span>
          <span className="le-plan-card__value">{roadmapLinked ? 'Yes' : 'No'}</span>
        </div>
        {orchestration ? (
          <>
            <div className="le-plan-card">
              <span className="le-plan-card__label">Graph completeness</span>
              <span className="le-plan-card__value">
                {orchestration.graph_completeness_score != null
                  ? `${orchestration.graph_completeness_score}%`
                  : '—'}
              </span>
            </div>
            <div className="le-plan-card">
              <span className="le-plan-card__label">Dep. pressure (graph)</span>
              <span className="le-plan-card__value">
                {orchestration.dependency_pressure_max ?? '—'}
              </span>
            </div>
            <div className="le-plan-card">
              <span className="le-plan-card__label">Critical path (d)</span>
              <span className="le-plan-card__value">
                {orchestration.critical_path?.ok ? orchestration.critical_path.length : '—'}
              </span>
            </div>
          </>
        ) : null}
      </div>
    </section>
  )
}
