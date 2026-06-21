import { describe, expect, it } from 'vitest'

import {
  isKnownUnstableOpenAiCompatModel,
  pickOpenAiCompatFallbackModel,
  sanitizeStudioModelOverride,
} from './copilotSessionPrefs'

describe('isKnownUnstableOpenAiCompatModel', () => {
  it('flags granite41-3b', () => {
    expect(isKnownUnstableOpenAiCompatModel('ctx-unlim-granite41-3b:latest')).toBe(true)
  })

  it('allows qwen ids', () => {
    expect(isKnownUnstableOpenAiCompatModel('ctx-unlim-qwen3-1p7b:latest')).toBe(false)
  })
})

describe('sanitizeStudioModelOverride', () => {
  it('clears known crash models', () => {
    expect(sanitizeStudioModelOverride('ctx-unlim-granite41-3b:latest', 'ctx-unlim-qwen3-1p7b:latest')).toBe('')
  })

  it('clears redundant copy of AI Setup main', () => {
    expect(sanitizeStudioModelOverride('ctx-unlim-qwen3-1p7b:latest', 'ctx-unlim-qwen3-1p7b:latest')).toBe('')
  })

  it('keeps intentional alternate override', () => {
    expect(sanitizeStudioModelOverride('ctx-unlim-qwen3-14b:latest', 'ctx-unlim-qwen3-1p7b:latest')).toBe(
      'ctx-unlim-qwen3-14b:latest',
    )
  })
})

describe('pickOpenAiCompatFallbackModel', () => {
  it('prefers qwen over granite alphabetically first', () => {
    expect(
      pickOpenAiCompatFallbackModel([
        'ctx-unlim-granite41-3b:latest',
        'ctx-unlim-qwen3-1p7b:latest',
      ]),
    ).toBe('ctx-unlim-qwen3-1p7b:latest')
  })
})
