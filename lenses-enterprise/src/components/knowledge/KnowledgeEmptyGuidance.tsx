import { Link } from 'react-router-dom'
import { STUDIO_VOCAB } from '../../nav/studioVisibleCopy'

/** Sample cards shown when methodology knowledge registries are empty. */
export const sampleCards = [
  {
    title: 'Charge log excerpt',
    hint: 'Capture a decision or outcome in charge markdown — it surfaces in workspace evidence browse.',
    to: '/workspace-md',
  },
  {
    title: 'ADR in repo docs',
    hint: 'Architecture decision records sync to the graph when orchestration is enabled.',
    to: '/tutorials',
  },
  {
    title: 'Plan → Story scope',
    hint: 'Link delivery work to methodology evidence from a scoped story.',
    to: '/plan?tab=story',
  },
] as const

type Props = {
  variant: 'evidence' | 'decisions'
}

/**
 * Humane emptyGuidance for Evidence / Decisions — sample cards + how to populate (no API jargon).
 */
export function KnowledgeEmptyGuidance({ variant }: Props) {
  const heading = variant === 'evidence' ? 'How to populate evidence' : 'How to populate decisions'

  return (
    <section className="le-card le-knowledge-empty-guidance" aria-label={heading}>
      <h2 className="le-cc-section__title">{heading}</h2>
      <p className="forge-support le-knowledge-empty-guidance__lead">
        {variant === 'evidence'
          ? 'Evidence grows from markdown you already keep — charge logs, journals, and methodology artifacts. Start with one file, rescan, and return here.'
          : 'Decisions appear when ADRs and sign-offs reach the methodology graph. Until then, draft in workspace notes and link from Plan.'}
      </p>
      <div className="le-card-grid le-knowledge-empty-guidance__sampleCards">
        {sampleCards.map((card) => (
          <article key={card.title} className="le-card le-knowledge-empty-guidance__card">
            <h3 style={{ fontSize: '0.95rem', margin: '0 0 0.35rem' }}>{card.title}</h3>
            <p className="forge-support" style={{ margin: '0 0 0.5rem' }}>
              {card.hint}
            </p>
            <Link className="le-btn le-btn--small" to={card.to}>
              Open
            </Link>
          </article>
        ))}
      </div>
      <p className="forge-support" style={{ marginTop: '0.75rem' }}>
        <Link to="/workspace-md">{STUDIO_VOCAB.workspaceNotes}</Link>
        {' · '}
        <Link to="/knowledge/agentic-bridge">Agentic bridge</Link>
      </p>
    </section>
  )
}
