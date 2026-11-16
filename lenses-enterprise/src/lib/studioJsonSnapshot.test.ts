import { describe, expect, it } from 'vitest'
import { formatSnapshotAge, readJsonSnapshot, snapshotStorageKey, writeJsonSnapshot } from './studioJsonSnapshot'

describe('studioJsonSnapshot', () => {
  it('round-trips through sessionStorage', () => {
    const key = `test-snap-${Date.now()}`
    writeJsonSnapshot(key, { a: 1 })
    const read = readJsonSnapshot<{ a: number }>(key)
    expect(read?.data).toEqual({ a: 1 })
    expect(typeof read?.fetchedAt).toBe('number')
    sessionStorage.removeItem(snapshotStorageKey(key))
  })

  it('formatSnapshotAge returns human phrases', () => {
    const now = 1_000_000_000_000
    expect(formatSnapshotAge(now - 30_000, now)).toBe('just now')
    expect(formatSnapshotAge(now - 120_000, now)).toMatch(/min/)
  })
})
