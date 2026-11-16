import { describe, expect, it } from 'vitest'
import { docsHealthEventKindLabel } from './docsHealthTimelineLabels'

describe('docsHealthEventKindLabel', () => {
  it('maps known kinds', () => {
    expect(docsHealthEventKindLabel('token_stats')).toBe('Token & model')
    expect(docsHealthEventKindLabel('file_inquiry')).toBe('File inquiry')
  })
  it('falls back for unknown kinds', () => {
    expect(docsHealthEventKindLabel('custom_event')).toBe('custom event')
  })
})
