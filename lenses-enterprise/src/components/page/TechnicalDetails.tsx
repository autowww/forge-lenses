import type { ReactNode } from 'react'

export const INSPECT_MODE_STORAGE_KEY = 'studio-inspect-admin'

/** True when Inspect surfaces are enabled (`?inspect=1` or localStorage flag). */
export function canShowTechnicalDetails(): boolean {
  if (typeof window === 'undefined') return false
  try {
    const params = new URLSearchParams(window.location.search)
    if (params.get('inspect') === '1') return true
    return window.localStorage.getItem(INSPECT_MODE_STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

/** Alias for {@link canShowTechnicalDetails} — use in conditional render blocks. */
export const showTechnical = canShowTechnicalDetails

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
 * Hidden unless Inspect mode is enabled.
 */
export function TechnicalDetails({
  summary = 'Technical details',
  children,
  className = '',
  defaultOpen = false,
}: TechnicalDetailsProps) {
  if (!canShowTechnicalDetails()) return null

  return (
    <details className={`le-technical-details${className ? ` ${className}` : ''}`} open={defaultOpen}>
      <summary className="le-technical-details__summary">{summary}</summary>
      <div className="le-technical-details__body">{children}</div>
    </details>
  )
}
