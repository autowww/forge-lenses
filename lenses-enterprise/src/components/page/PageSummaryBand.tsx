import type { ReactNode } from 'react'

export type PageSummaryBandProps = {
  children: ReactNode
  className?: string
  /** Landmark label for assistive tech (e.g. "Page summary"). */
  'aria-label'?: string
}

/** First content band after the header — KPIs, snapshot cards, or a short summary stack. */
export function PageSummaryBand({ children, className = '', 'aria-label': ariaLabel }: PageSummaryBandProps) {
  return (
    <div className={`le-page-summary-band${className ? ` ${className}` : ''}`} role="region" aria-label={ariaLabel}>
      {children}
    </div>
  )
}
