import { FULL_WORKSPACE_UI, STUDIO_GLOSSARY, STUDIO_VOCAB } from '../../nav/studioVisibleCopy'

type Props = {
  classicPlanHref: string
}

export function SourceContext({ classicPlanHref }: Props) {
  return (
    <section className="le-plan-section" aria-labelledby="le-plan-source-h">
      <h2 id="le-plan-source-h" className="le-plan-section__title">
        {STUDIO_VOCAB.sources}
      </h2>
      <p className="le-plan-section__lead">{STUDIO_GLOSSARY.sources.long}</p>
      <p className="forge-support">
        <a href={classicPlanHref}>{FULL_WORKSPACE_UI.openPlanSameQuery}</a>
      </p>
    </section>
  )
}
