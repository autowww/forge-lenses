import { describe, expect, it } from 'vitest'
import {
  WIZARD_STEP_COUNT,
  WIZARD_STEPS,
  clampStepIndex,
  getStepTitle,
  stepIndexBack,
  stepIndexNext,
} from './wizardSteps'

describe('WIZARD_STEPS', () => {
  it('has 12 steps with expected first and last titles', () => {
    expect(WIZARD_STEP_COUNT).toBe(12)
    expect(WIZARD_STEPS[0]).toBe('Mission')
    expect(WIZARD_STEPS[11]).toBe('Experimental Build')
  })
})

describe('clampStepIndex', () => {
  it('clamps to 0..11', () => {
    expect(clampStepIndex(-99)).toBe(0)
    expect(clampStepIndex(0)).toBe(0)
    expect(clampStepIndex(11)).toBe(11)
    expect(clampStepIndex(99)).toBe(11)
  })
})

describe('stepIndexNext / stepIndexBack', () => {
  it('steps within range', () => {
    expect(stepIndexNext(0)).toBe(1)
    expect(stepIndexBack(1)).toBe(0)
  })

  it('does not pass ends', () => {
    expect(stepIndexNext(11)).toBe(11)
    expect(stepIndexBack(0)).toBe(0)
  })
})

describe('getStepTitle', () => {
  it('returns title for valid index', () => {
    expect(getStepTitle(0)).toBe('Mission')
    expect(getStepTitle(5)).toBe('Target & Output Pack')
  })

  it('clamps out-of-range index', () => {
    expect(getStepTitle(999)).toBe('Experimental Build')
  })
})
