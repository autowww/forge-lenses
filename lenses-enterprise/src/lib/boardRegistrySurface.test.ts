import { describe, expect, it } from 'vitest'
import { classifyBoardRegistryData, formatRegistrySnapshotLabel } from './boardRegistrySurface'

describe('classifyBoardRegistryData', () => {
  it('returns none for null', () => {
    expect(classifyBoardRegistryData(null)).toBe('none')
  })

  it('returns empty for zero boards and clean payload', () => {
    expect(
      classifyBoardRegistryData({
        projects: {},
        validation_issues: [],
      }),
    ).toBe('empty')
  })

  it('returns partial when validation_issues present', () => {
    expect(
      classifyBoardRegistryData({
        projects: { r: [{ id: 'b1', label: 'B', storage: 'local' }] },
        validation_issues: ['missing_board_files:x'],
      }),
    ).toBe('partial')
  })

  it('returns partial when access_enforced', () => {
    expect(
      classifyBoardRegistryData({
        projects: { r: [{ id: 'b1', label: 'B', storage: 'local' }] },
        access_enforced: true,
      }),
    ).toBe('partial')
  })

  it('returns loaded when rows exist and clean', () => {
    expect(
      classifyBoardRegistryData({
        projects: { r: [{ id: 'b1', label: 'B', storage: 'local' }] },
        validation_issues: [],
      }),
    ).toBe('loaded')
  })
})

describe('formatRegistrySnapshotLabel', () => {
  it('formats ISO', () => {
    const s = formatRegistrySnapshotLabel('2026-04-01T12:00:00.000Z')
    expect(s).not.toBe('—')
    expect(s.length).toBeGreaterThan(4)
  })

  it('returns dash for empty', () => {
    expect(formatRegistrySnapshotLabel(null)).toBe('—')
  })
})
