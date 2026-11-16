import type { PlanMilestone } from '../../lib/planMetrics'
import { getWorkModelStats } from '../../lib/planMetrics'

type Props = {
  workModel: Record<string, unknown> | null
  milestones: PlanMilestone[]
  onSelectRoot: (id: string) => void
}

export function WbsCoverage({ workModel, milestones, onSelectRoot }: Props) {
  const { rootIds, nodeCount, rootCount } = getWorkModelStats(workModel)
  const storyTotal = milestones.reduce((n, ms) => n + (ms.stories?.length ?? 0), 0)

  return (
    <section className="le-plan-section" aria-labelledby="le-plan-wbs-h">
      <h2 id="le-plan-wbs-h" className="le-plan-section__title">
        WBS coverage and breakdown
      </h2>
      <p className="le-plan-section__lead">
        Work graph from forge-work-model: roots anchor the tree; nodes are drillable from the Plan tab.
      </p>
      {!workModel ? (
        <p className="le-plan-section__empty">Load a WBS to see the work model.</p>
      ) : (
        <>
          <ul className="le-plan-wbs-stats">
            <li>
              <strong>{rootCount}</strong> root node(s)
            </li>
            <li>
              <strong>{nodeCount}</strong> total node(s)
            </li>
            <li>
              <strong>{storyTotal}</strong> stor{storyTotal === 1 ? 'y' : 'ies'} listed under spine milestones
            </li>
          </ul>
          {rootIds.length > 0 && (
            <>
              <h3 className="le-plan-subtitle">Root nodes</h3>
              <ul className="le-plan-root-list">
                {rootIds.map((rid) => (
                  <li key={rid}>
                    <button type="button" className="le-btn le-btn--small" onClick={() => onSelectRoot(rid)}>
                      {rid}
                    </button>
                  </li>
                ))}
              </ul>
            </>
          )}
        </>
      )}
    </section>
  )
}
