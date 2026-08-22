import type { ReactNode } from 'react'
import type { ClassifiedFetchFailure } from '../../lib/classifyFetchError'

export type DataResilienceBarProps = {
  variant: 'stale' | 'error'
  failure: ClassifiedFetchFailure | null
  snapshotAtMs: number | null
  snapshotTimeLabel: string | null
  snapshotAgeLabel: string | null
  onRetry: () => void
  /** Secondary actions (e.g. link to dashboard) */
  extraActions?: ReactNode
}

/**
 * Single compact strip for degraded data — avoids repeating full `StatePanel` error blocks per card.
 */
export function DataResilienceBar({
  variant,
  failure,
  snapshotAtMs,
  snapshotTimeLabel,
  snapshotAgeLabel,
  onRetry,
  extraActions,
}: DataResilienceBarProps) {
  const reason = failure?.summary ?? 'Could not refresh data.'
  const technical =
    [failure?.detail, failure?.httpStatus != null ? `Response status: ${failure.httpStatus}` : null]
      .filter((x): x is string => Boolean(x && String(x).trim()))
      .join('\n') || null

  return (
    <div
      className={`le-data-resilience-bar le-data-resilience-bar--${variant}`}
      role="status"
    >
      <div className="le-data-resilience-bar__text">
        {variant === 'stale' && snapshotTimeLabel ? (
          <>
            <strong>Viewing a saved copy.</strong> {reason} Showing last good data from{' '}
            <time dateTime={snapshotAtMs != null ? new Date(snapshotAtMs).toISOString() : undefined}>
              {snapshotTimeLabel}
            </time>
            {snapshotAgeLabel ? ` (${snapshotAgeLabel})` : ''} stored in this browser.
            {technical ? (
              <details className="le-data-resilience-bar__technical">
                <summary>Show technical details</summary>
                <pre className="le-data-resilience-bar__technical-pre">{technical}</pre>
              </details>
            ) : null}
          </>
        ) : (
          <>
            <strong>Data unavailable.</strong> {reason}
            {technical ? (
              <details className="le-data-resilience-bar__technical">
                <summary>Show technical details</summary>
                <pre className="le-data-resilience-bar__technical-pre">{technical}</pre>
              </details>
            ) : null}
          </>
        )}
      </div>
      <div className="le-data-resilience-bar__actions">
        <button type="button" className="le-btn le-btn--small le-btn--primary" onClick={onRetry}>
          Retry
        </button>
        {extraActions}
      </div>
    </div>
  )
}
