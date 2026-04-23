import { TechnicalDetails } from '../page'
import { FULL_WORKSPACE_UI, STUDIO_VOCAB } from '../../nav/studioVisibleCopy'

type Props = {
  roadmapP: string
  classicPlanHref: string
  roadmapSummaryHref: string | null
}

export function RoadmapTrace({ roadmapP, classicPlanHref, roadmapSummaryHref }: Props) {
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
          <TechnicalDetails summary="Classic workspace roadmap previews (optional)" defaultOpen={false}>
            <ul className="le-plan-trace-links">
              {roadmapSummaryHref ? (
                <li>
                  <a href={roadmapSummaryHref}>Roadmaps summary (charts fragment)</a>
                </li>
              ) : null}
              <li>
                <a href={classicPlanHref}>{FULL_WORKSPACE_UI.openPlanSameQuery}</a> — {STUDIO_VOCAB.sources} tab and
                roadmap outline.
              </li>
            </ul>
          </TechnicalDetails>
        </>
      )}
    </section>
  )
}
