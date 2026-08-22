import { TechnicalDetails } from '../page'
import { STUDIO_VOCAB } from '../../nav/studioVisibleCopy'

type Props = {
  roadmapP: string
  roadmapSummaryHref: string | null
}

export function RoadmapTrace({ roadmapP, roadmapSummaryHref }: Props) {
  const hasRm = Boolean(roadmapP.trim())

  return (
    <section className="le-plan-section" aria-labelledby="le-plan-trace-h">
      <h2 id="le-plan-trace-h" className="le-plan-section__title">
        Roadmap trace
      </h2>
      <p className="le-plan-section__lead">
        Connect {STUDIO_VOCAB.plan} intent to your {STUDIO_VOCAB.roadmap} narrative for this scope.
      </p>
      {!hasRm ? (
        <p className="le-plan-section__empty">
          No roadmap file selected — pick one in scope to align commitments with ROADMAP.md.
        </p>
      ) : (
        <>
          <p className="forge-support">
            <strong>Roadmap file:</strong> <code className="le-mono">{roadmapP}</code>
          </p>
          {roadmapSummaryHref ? (
            <TechnicalDetails summary="Roadmap previews (optional)" defaultOpen={false}>
              <ul className="le-plan-trace-links">
                <li>
                  <a href={roadmapSummaryHref}>Roadmaps summary (charts fragment)</a>
                </li>
              </ul>
            </TechnicalDetails>
          ) : null}
        </>
      )}
    </section>
  )
}
