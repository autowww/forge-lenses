import type { ReactNode } from 'react'

export type PageAiInsightCardProps = {
  title?: string
  whatChanged?: ReactNode
  whyItMatters?: ReactNode
  nextAction?: ReactNode
  className?: string
}

/**
 * Compact supportive summary — not a second hero; use below the page header or summary band.
 */
export function PageAiInsightCard({
  title = 'Suggested focus',
  whatChanged,
  whyItMatters,
  nextAction,
  className = '',
}: PageAiInsightCardProps) {
  if (!whatChanged && !whyItMatters && !nextAction) return null
  return (
    <section
      className={`le-page-ai-insight${className ? ` ${className}` : ''}`}
      aria-label={title}
    >
      <h2 className="le-page-ai-insight__title">{title}</h2>
      {whatChanged ? (
        <p className="le-page-ai-insight__row">
          <span className="le-page-ai-insight__k">What changed</span>
          <span className="le-page-ai-insight__v">{whatChanged}</span>
        </p>
      ) : null}
      {whyItMatters ? (
        <p className="le-page-ai-insight__row">
          <span className="le-page-ai-insight__k">Why it matters</span>
          <span className="le-page-ai-insight__v">{whyItMatters}</span>
        </p>
      ) : null}
      {nextAction ? (
        <div className="le-page-ai-insight__next">
          <span className="le-page-ai-insight__k">Next</span>
          <div className="le-page-ai-insight__v">{nextAction}</div>
        </div>
      ) : null}
    </section>
  )
}
