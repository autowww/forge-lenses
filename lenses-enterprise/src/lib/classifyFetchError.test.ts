import { describe, expect, it } from 'vitest'
import { ApiError } from '../api/http'
import { classifyFetchError, isTransientCopilotTransportError } from './classifyFetchError'

describe('classifyFetchError', () => {
  it('maps 403 to permission', () => {
    const c = classifyFetchError(new ApiError('Access not allowed', 403, 'code: forbidden'))
    expect(c.kind).toBe('permission')
    expect(c.httpStatus).toBe(403)
    expect(c.summary).toBe('Access not allowed')
    expect(c.detail).toContain('forbidden')
  })

  it('maps 404 to not_found', () => {
    expect(classifyFetchError(new ApiError('missing', 404)).kind).toBe('not_found')
  })

  it('maps 503 to server', () => {
    expect(classifyFetchError(new ApiError('busy', 503)).kind).toBe('server')
  })

  it('maps TypeError fetch failures to network', () => {
    const c = classifyFetchError(new TypeError('Failed to fetch'))
    expect(c.kind).toBe('network')
  })
})

describe('isTransientCopilotTransportError', () => {
  it('is true for SSE drop and timeout messages from the copilot rail', () => {
    expect(isTransientCopilotTransportError(new Error('SSE connection lost'))).toBe(true)
    expect(isTransientCopilotTransportError(new Error('Copilot stream timed out.'))).toBe(true)
  })

  it('is true for flaky fetch TypeErrors', () => {
    expect(isTransientCopilotTransportError(new TypeError('Failed to fetch'))).toBe(true)
  })

  it('is true for gateway overload HTTP statuses', () => {
    expect(isTransientCopilotTransportError(new ApiError('bad', 502))).toBe(true)
    expect(isTransientCopilotTransportError(new ApiError('bad', 503))).toBe(true)
    expect(isTransientCopilotTransportError(new ApiError('bad', 504))).toBe(true)
  })

  it('is false for auth and client errors', () => {
    expect(isTransientCopilotTransportError(new ApiError('no', 403))).toBe(false)
    expect(isTransientCopilotTransportError(new ApiError('no', 404))).toBe(false)
    expect(isTransientCopilotTransportError(new Error('stream_error'))).toBe(false)
  })
})
