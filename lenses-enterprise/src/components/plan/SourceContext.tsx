import { STUDIO_GLOSSARY, STUDIO_VOCAB } from '../../nav/studioVisibleCopy'

export function SourceContext() {
  return (
    <section className="le-plan-section" aria-labelledby="le-plan-source-h">
      <h2 id="le-plan-source-h" className="le-plan-section__title">
        {STUDIO_VOCAB.sources}
      </h2>
      <p className="le-plan-section__lead">{STUDIO_GLOSSARY.sources.long}</p>
    </section>
  )
}
