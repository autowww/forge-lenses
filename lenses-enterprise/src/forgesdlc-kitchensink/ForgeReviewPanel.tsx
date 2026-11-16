import type { ReactNode } from 'react'

export type ForgeReviewPanelProps = {
  title?: string
  /** Optional eyebrow or context above the title. */
  kicker?: ReactNode
  children: ReactNode
  className?: string
}

/**
 * Optional reusable review surface — diff / code / diagram / approval layouts; host fills children.
 */
export function ForgeReviewPanel({ title = 'Review', kicker, children, className = '' }: ForgeReviewPanelProps) {
  return (
    <section className={`ks-fe-review ${className}`.trim()} aria-label={title}>
      {kicker ? <div className="ks-fe-review__kicker">{kicker}</div> : null}
      <h3 className="ks-fe-review__title">{title}</h3>
      <div className="ks-fe-review__body">{children}</div>
    </section>
  )
}
