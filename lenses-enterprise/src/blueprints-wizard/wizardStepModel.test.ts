import { describe, expect, it } from 'vitest'
import type { WizardSessionDocumentJson } from '../api/blueprintsWizard'
import {
  WIZARD_STEP_COUNT,
  applyStepBack,
  applyStepNext,
  clampStepIndex,
  getStepNote,
  setStepNote,
} from './wizardStepModel'

function doc(over: Partial<WizardSessionDocumentJson> = {}): WizardSessionDocumentJson {
  return {
    version: 1,
    updated_at: '2026-01-01T00:00:00Z',
    step_index: 0,
    payload: {},
    ...over,
  }
}

describe('clampStepIndex', () => {
  it('clamps to step range', () => {
    expect(clampStepIndex(-1)).toBe(0)
    expect(clampStepIndex(0)).toBe(0)
    expect(clampStepIndex(WIZARD_STEP_COUNT - 1)).toBe(WIZARD_STEP_COUNT - 1)
    expect(clampStepIndex(99)).toBe(WIZARD_STEP_COUNT - 1)
  })
})

describe('applyStepNext / applyStepBack', () => {
  it('increments and preserves payload', () => {
    const s = doc({ step_index: 0, payload: { stepNotes: { '0': 'a' } } })
    const n = applyStepNext(s)
    expect(n.step_index).toBe(1)
    expect(getStepNote(n.payload, 0)).toBe('a')
  })

  it('does not pass last step', () => {
    const s = doc({ step_index: WIZARD_STEP_COUNT - 1 })
    expect(applyStepNext(s).step_index).toBe(WIZARD_STEP_COUNT - 1)
  })

  it('decrements from middle', () => {
    const s = doc({ step_index: 2 })
    expect(applyStepBack(s).step_index).toBe(1)
  })

  it('does not pass first step', () => {
    const s = doc({ step_index: 0 })
    expect(applyStepBack(s).step_index).toBe(0)
  })
})

describe('step notes', () => {
  it('getStepNote and setStepNote round-trip', () => {
    const s = doc()
    const u = setStepNote(s, 1, 'hello')
    expect(getStepNote(u.payload, 1)).toBe('hello')
    expect(getStepNote(u.payload, 0)).toBe('')
  })
})
