import { describe, expect, it } from 'vitest'
import {
  STALE_DAYS_THRESHOLD,
  flattenRegistryToRows,
  isBoardFresh,
  isBoardStale,
  isUnowned,
} from './boardDirectory'

describe('flattenRegistryToRows', () => {
  it('flattens projects and normalizes fields', () => {
    const rows = flattenRegistryToRows({
      projects: {
        myrepo: [
          {
            id: 'abc123',
            label: 'Test',
            storage: 'local',
            owner_login: 'alice',
            editors: ['bob'],
            preview_mtime: '2025-01-01T00:00:00Z',
          },
        ],
      },
    })
    expect(rows).toHaveLength(1)
    expect(rows[0].project).toBe('myrepo')
    expect(rows[0].ownerLogin).toBe('alice')
    expect(rows[0].editorsCount).toBe(1)
    expect(rows[0].viewersCount).toBe(0)
  })
})

describe('isUnowned', () => {
  it('is true without owner', () => {
    expect(
      isUnowned({
        id: 'x',
        label: 'L',
        storage: 'local',
        project: 'p',
        ownerLogin: null,
        editorsCount: 0,
        viewersCount: 0,
        previewMtime: null,
      }),
    ).toBe(true)
  })
})

describe('isBoardStale', () => {
  const now = new Date('2025-06-01T12:00:00Z')

  it('treats missing mtime as stale', () => {
    expect(
      isBoardStale(
        {
          id: 'x',
          label: 'L',
          storage: 'local',
          project: 'p',
          ownerLogin: null,
          editorsCount: 0,
          viewersCount: 0,
          previewMtime: null,
        },
        now,
        STALE_DAYS_THRESHOLD,
      ),
    ).toBe(true)
  })

  it('treats old mtime as stale', () => {
    const old = new Date('2025-01-01T00:00:00Z').toISOString()
    expect(
      isBoardStale(
        {
          id: 'x',
          label: 'L',
          storage: 'local',
          project: 'p',
          ownerLogin: null,
          editorsCount: 0,
          viewersCount: 0,
          previewMtime: old,
        },
        now,
        60,
      ),
    ).toBe(true)
  })

  it('treats recent mtime as fresh', () => {
    const recent = new Date('2025-05-30T00:00:00Z').toISOString()
    expect(
      isBoardStale(
        {
          id: 'x',
          label: 'L',
          storage: 'local',
          project: 'p',
          ownerLogin: null,
          editorsCount: 0,
          viewersCount: 0,
          previewMtime: recent,
        },
        now,
        60,
      ),
    ).toBe(false)
  })
})

describe('isBoardFresh', () => {
  const now = new Date('2025-06-01T12:00:00Z')

  it('is opposite of stale for recent mtime', () => {
    const recent = new Date('2025-05-30T00:00:00Z').toISOString()
    const row = {
      id: 'x',
      label: 'L',
      storage: 'local' as const,
      project: 'p',
      ownerLogin: 'a',
      editorsCount: 0,
      viewersCount: 0,
      previewMtime: recent,
    }
    expect(isBoardFresh(row, now, 60)).toBe(true)
    expect(isBoardStale(row, now, 60)).toBe(false)
  })
})
