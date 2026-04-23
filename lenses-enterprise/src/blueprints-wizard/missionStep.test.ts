import { describe, expect, it } from 'vitest'
import {
  emptyMissionPayload,
  formatMissionForStepNote,
  missionModeToMissionType,
  missionTypeToMissionMode,
  parseMissionFromPayload,
  validateMissionForNext,
} from './missionStep'

describe('validateMissionForNext', () => {
  it('requires title and outcome', () => {
    const r = validateMissionForNext(emptyMissionPayload())
    expect(r.ok).toBe(false)
    expect(r.errors.title).toBeDefined()
    expect(r.errors.outcome).toBeDefined()
  })

  it('passes with trimmed title and outcome', () => {
    const r = validateMissionForNext({
      mode: 'start_from_idea',
      title: '  My mission  ',
      outcome: 'Ship the thing.',
      notes: '',
    })
    expect(r.ok).toBe(true)
  })
})

describe('parseMissionFromPayload', () => {
  it('reads mission object including mode', () => {
    const m = parseMissionFromPayload({
      mission: { mode: 'repair_stage', title: 'T', outcome: 'O', notes: 'N' },
    })
    expect(m).toEqual({ mode: 'repair_stage', title: 'T', outcome: 'O', notes: 'N' })
  })
})

describe('formatMissionForStepNote', () => {
  it('joins non-empty parts', () => {
    const s = formatMissionForStepNote({
      mode: 'assess_current_project',
      title: 'A',
      outcome: 'B',
      notes: 'C',
    })
    expect(s).toContain('Mode:')
    expect(s).toContain('Mission: A')
    expect(s).toContain('Outcome: B')
    expect(s).toContain('Notes: C')
  })
})

describe('missionModeToMissionType', () => {
  it('maps wizard modes to domain types', () => {
    expect(missionModeToMissionType('start_from_idea')).toBe('explore')
    expect(missionModeToMissionType('resume_advance')).toBe('deliver')
  })
})

describe('missionTypeToMissionMode', () => {
  it('maps domain types back for legacy sessions', () => {
    expect(missionTypeToMissionMode('define')).toBe('assess_current_project')
    expect(missionTypeToMissionMode('sunset')).toBe('start_from_idea')
  })
})
