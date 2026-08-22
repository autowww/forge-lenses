import { describe, expect, it } from 'vitest'
import { appendAssumptionEntry, removeAssumptionById, updateAssumptionEntry } from './wizardAssumptionHelpers'

describe('wizardAssumptionHelpers', () => {
  it('appendAssumptionEntry assigns id and normalizes', () => {
    const next = appendAssumptionEntry([], { text: 'A' })
    expect(next.length).toBe(1)
    expect(next[0].text).toBe('A')
    expect(next[0].id.length).toBeGreaterThan(4)
  })

  it('removeAssumptionById filters', () => {
    const a = appendAssumptionEntry([], { text: 'x' })
    const id = a[0].id
    expect(removeAssumptionById(a, id)).toEqual([])
  })

  it('updateAssumptionEntry patches text', () => {
    const a = appendAssumptionEntry([], { text: 'a' })
    const id = a[0].id
    const u = updateAssumptionEntry(a, id, { text: 'b' })
    expect(u[0].text).toBe('b')
  })
})
