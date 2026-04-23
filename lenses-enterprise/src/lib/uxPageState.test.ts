import { describe, expect, it } from 'vitest'
import { ApiError } from '../api/http'
import { assistShortcutsForContext, resolveUxFailure } from './uxPageState'
describe('resolveUxFailure', () => {
  it('maps network errors to user-first title', () => {
    const r = resolveUxFailure(new TypeError('Failed to fetch'))
    expect(r.title).toBe('This data source is unavailable right now')
    expect(r.description).toMatch(/workspace service/i)
  })

  it('maps API 503 to unavailable title', () => {
    const r = resolveUxFailure(new ApiError('x', 503, 'upstream'))
    expect(r.title).toBe('This data source is unavailable right now')
  })
})

describe('assistShortcutsForContext', () => {
  it('returns four guided prompts', () => {
    const a = assistShortcutsForContext({ context: 'Evidence registry', detail: 'Graph off.' })
    expect(a).toHaveLength(4)
    expect(a[0].label).toBe('Explain this state')
    expect(a[0].prompt).toContain('Evidence registry')
  })
})

describe('classifyFetchError + resolveUxFailure', () => {
  it('keeps permission copy under permission title', () => {
    const u = resolveUxFailure(new ApiError('No access', 403, 'forbidden'))
    expect(u.kind).toBe('permission_denied')
    expect(u.title).toBe('Permission required')
  })
})
