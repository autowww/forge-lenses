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
    if (/stream timed out/i.test(m)) return true
  }
  return false
}

export type CopilotFailureLike = {
  ok?: boolean
  error?: string | null
  detail?: string | null
  text?: string | null
  message?: string | null
}

const NON_RETRIABLE_COPILOT_CODES = new Set([
  'feature_disabled',
  'invalid_tool_mode',
  'missing_message',
  'forbidden',
  'permission_denied',
])

/**
 * True when repeating the same Copilot turn may succeed (gateway runner crash, timeout, flaky SSE, etc.).
 * Used by Lenses Copilot auto-retry; auth/validation failures are not retried.
 */
export function isRetriableCopilotFailure(err: unknown): boolean {
  if (err instanceof ApiError) {
    if (err.status === 403 || err.status === 404 || err.status === 401) return false
    return isTransientCopilotTransportError(err)
  }
  if (isTransientCopilotTransportError(err)) return true

  if (typeof err === 'object' && err !== null) {
    const o = err as CopilotFailureLike
    if (o.ok === true && (o.text || '').trim()) return false

    const code = String(o.error || '')
      .trim()
      .toLowerCase()
    if (code && NON_RETRIABLE_COPILOT_CODES.has(code)) return false

    const parts = [o.detail, o.error, o.message].filter(
      (x) => typeof x === 'string' && x.trim(),
    ) as string[]
    const raw = parts.join(' ').toLowerCase()

    if (
      raw.includes('llama runner') ||
      raw.includes('runner process') ||
      raw.includes('terminated') ||
      raw.includes('out of memory') ||
      /\boom\b/.test(raw)
    ) {
      return true
    }
    if (code === 'llm_provider_error' || code === 'stream_timeout' || code === 'stream_error') {
      return true
    }
    if (/timed out|timeout|connection reset|econnreset|bad gateway|service unavailable/i.test(raw)) {
      return true
    }
    if (o.ok === false || !(o.text || '').trim()) return true
    return false
  }

  if (err instanceof Error) {
    const m = err.message.toLowerCase()
    if (m === 'sse connection lost') return true
    if (/stream timed out|llama runner|runner process|terminated|out of memory|timed out/i.test(m)) {
      return true
    }
  }

  return false
}

/** User-facing message after automatic retries are exhausted. */
export function formatCopilotExhaustedAttemptsMessage(reason: string, attempts: number): string {
  const body = reason.trim() || 'The model did not return a response.'
  const lower = body.toLowerCase()
  let hint =
    'You can tap Retry, or pick a stable model in Copilot settings (gear).'
  if (lower.includes('sse connection') || lower.includes('stream timed out')) {
    hint =
      'The connection dropped while waiting for the model — Retry usually works. For long portfolio questions, use AI Setup default model or read-only mode.'
  } else if (
    lower.includes('llama runner') ||
    lower.includes('runner process') ||
    lower.includes('terminated') ||
    lower.includes('out of memory')
  ) {
    hint =
      'The gateway model crashed — clear the Model override in Copilot settings (gear) to use your AI Setup default.'
  }
  return (
    `Failed after ${attempts} attempts in a row.\n\n${body}\n\n${hint}`
  )
}

/** Thrown inside Copilot send loops to signal a failed attempt (may auto-retry). */
export class CopilotAttemptFailure extends Error {
  readonly userMessage: string
  readonly retriable: boolean

  constructor(userMessage: string, retriable: boolean) {
    super(userMessage)
    this.name = 'CopilotAttemptFailure'
    this.userMessage = userMessage
    this.retriable = retriable
  }
}

export function copilotAttemptFailureFromUnknown(err: unknown, fallback: string): CopilotAttemptFailure {
  if (err instanceof CopilotAttemptFailure) return err
  if (err instanceof ApiError && err.status === 403) {
    return new CopilotAttemptFailure(err.message, false)
  }
  const ux = classifyFetchError(err)
  const msg = ux.detail && ux.detail !== ux.summary ? `${ux.summary} ${ux.detail}` : ux.summary
  return new CopilotAttemptFailure(msg || fallback, isRetriableCopilotFailure(err))
}
