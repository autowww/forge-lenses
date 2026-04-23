import { ApiError } from '../api/http'

export type FetchFailureKind =
  | 'permission'
  | 'not_found'
  | 'network'
  | 'server'
  | 'scan'
  | 'unknown'

export type ClassifiedFetchFailure = {
  kind: FetchFailureKind
  /** Short user-facing line */
  summary: string
  /** Original message when useful */
  detail?: string
  httpStatus?: number
}

function apiErrorKind(status: number): FetchFailureKind {
  if (status === 401 || status === 403) return 'permission'
  if (status === 404) return 'not_found'
  if (status === 503 || status === 502 || status === 504) return 'server'
  if (status >= 500) return 'server'
  return 'unknown'
}

/**
 * Map thrown errors into IA copy buckets. `ApiError.message` is already user-safe (from `api/http.ts`).
 */
export function classifyFetchError(err: unknown): ClassifiedFetchFailure {
  if (err instanceof ApiError) {
    const s = err.status
    return {
      kind: apiErrorKind(s),
      summary: err.message,
      detail: err.technicalNote ?? undefined,
      httpStatus: s,
    }
  }
  if (err instanceof TypeError && typeof err.message === 'string') {
    if (/network|fetch|Failed to fetch|Load failed/i.test(err.message)) {
      return {
        kind: 'network',
        summary: 'The workspace service did not respond.',
        detail: err.message,
      }
    }
  }
  const msg = err instanceof Error ? err.message : String(err)
  return { kind: 'unknown', summary: 'Something went wrong loading data.', detail: msg }
}

/**
 * True when repeating the same Copilot request may succeed (flaky SSE, brief gateway overload, etc.).
 * Used by Lenses Copilot rail auto-retry; do not use for logical/API validation failures.
 */
export function isTransientCopilotTransportError(err: unknown): boolean {
  if (err instanceof ApiError) {
    const s = err.status
    return s === 502 || s === 503 || s === 504
  }
  if (err instanceof TypeError && typeof err.message === 'string') {
    if (/network|fetch|Failed to fetch|Load failed/i.test(err.message)) return true
  }
  if (err instanceof Error) {
    const m = err.message
    if (m === 'SSE connection lost') return true
    if (m === 'Copilot stream timed out.') return true
  }
  return false
}
