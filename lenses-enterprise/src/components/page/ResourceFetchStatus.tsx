import type { ReactNode } from 'react'
import { StatePanel } from './StatePanel'

export type ResourceFetchStatusProps = {
  resourceLabel: string
  isFetching: boolean
  hasDisplayPayload: boolean
  isHydrating: boolean
  lastError: string | null
  servingFromCacheAfterFailure: boolean
  snapshotAtLabel: string | null
  onRetry: () => void
  recoveryActions?: ReactNode
  className?: string
}

/**
 * Shared band for resource-backed Studio pages: initial load, background refresh, hard failures,
 * and stale-cache recovery — keeps hubs decision-ready instead of a single full-page spinner.
 */
export function ResourceFetchStatus({
  resourceLabel,
  isFetching,
  hasDisplayPayload,
  isHydrating,
  lastError,
  servingFromCacheAfterFailure,
  snapshotAtLabel,
  onRetry,
  recoveryActions,
  className = '',
}: ResourceFetchStatusProps) {
  const initialLoading = isHydrating && isFetching && !hasDisplayPayload
  const softRefresh = hasDisplayPayload && isFetching
  const staleBanner =
    Boolean(lastError) &&
    !isFetching &&
    servingFromCacheAfterFailure &&
    hasDisplayPayload &&
    Boolean(snapshotAtLabel)
  const hardFailure = Boolean(lastError) && !isFetching && !hasDisplayPayload && !isHydrating

  if (!initialLoading && !softRefresh && !staleBanner && !hardFailure) {
    return null
  }

  return (
    <div className={`le-resource-fetch-status ${className}`.trim()}>
      {initialLoading ? (
        <StatePanel
          variant="loading"
          density="compact"
          title={`Loading ${resourceLabel}`}
          description="Shortcuts and create actions below stay available while this request finishes."
        />
      ) : null}

      {softRefresh ? (
        <p className="le-resource-fetch-status__inline" role="status">
          <span className="le-resource-fetch-status__dot" aria-hidden="true" />
          Refreshing {resourceLabel}…
        </p>
      ) : null}

      {staleBanner ? (
        <StatePanel
          variant="stale"
          density="compact"
          title="Showing last saved boards list"
          description={`Saved at ${snapshotAtLabel}. Live refresh didn’t succeed — the list below may be out of date until you retry.`}
          technicalDetail={lastError}
          actions={
            <>
              <button type="button" className="le-btn le-btn--primary" onClick={() => void onRetry()}>
                Retry
              </button>
              {recoveryActions}
            </>
          }
          telemetryTag="boards-registry-stale-cache"
        />
      ) : null}

      {hardFailure ? (
        <StatePanel
          variant="error"
          density="compact"
          title="Couldn’t load this boards list"
          description={`${resourceLabel} didn’t load. Confirm Lenses is running, then retry.`}
          technicalDetail={lastError}
          actions={
            <>
              <button type="button" className="le-btn le-btn--primary" onClick={() => void onRetry()}>
                Retry
              </button>
              {recoveryActions}
            </>
          }
          telemetryTag="boards-registry-hard-failure"
        />
      ) : null}
    </div>
  )
}
