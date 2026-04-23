import type { ReactNode } from 'react'

export type TechnicalDetailsProps = {
  /** Visible summary control (default matches Studio copy for implementation/debug blocks). */
  summary?: ReactNode
  children: ReactNode
  className?: string
  /** When true, starts expanded (prefer false for progressive disclosure). */
  defaultOpen?: boolean
}

/**
 * Collapsed-by-default block for paths, endpoints, raw JSON, and session internals.
 */
export function TechnicalDetails({
  summary = 'Technical details',
  children,
  className = '',
  defaultOpen = false,
}: TechnicalDetailsProps) {
  return (
    <details className={`le-technical-details${className ? ` ${className}` : ''}`} open={defaultOpen}>
      <summary className="le-technical-details__summary">{summary}</summary>
      <div className="le-technical-details__body">{children}</div>
    </details>
  )
}
