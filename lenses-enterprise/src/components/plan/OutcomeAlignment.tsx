import type { OutcomeAlignment as OA } from '../../lib/planMetrics'

type Props = {
  alignment: OA
}

export function OutcomeAlignment({ alignment }: Props) {
  const { storyIdsInSpine, matchedInWorkModel, coveragePct } = alignment

  return (
    <section className="le-plan-section" aria-labelledby="le-plan-outcome-h">
      <h2 id="le-plan-outcome-h" className="le-plan-section__title">
        Outcome alignment
      </h2>
      <p className="le-plan-section__lead">
        Heuristic: spine story rows that also appear as nodes in the forge work model (IDs must match).
      </p>
      {storyIdsInSpine === 0 ? (
        <p className="le-plan-section__empty">No stories listed under milestones in the spine yet.</p>
      ) : (
        <p className="le-plan-alignment">
          <strong>{matchedInWorkModel}</strong> of <strong>{storyIdsInSpine}</strong> spine stories have a
          matching work-model node
          {coveragePct != null ? (
            <>
              {' '}
              (<strong>{coveragePct}%</strong> coverage)
            </>
          ) : null}
          .
        </p>
      )}
    </section>
  )
}
