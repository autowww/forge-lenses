import { describe, expect, it } from 'vitest'
import {
  artifactPackFromTargetPayload,
  emptyTargetOutputPackPayload,
  formatTargetOutputPackForStepNote,
  validateTargetOutputPackForNext,
} from './targetOutputPackStep'

describe('validateTargetOutputPackForNext', () => {
  it('requires artifacts', () => {
    const r = validateTargetOutputPackForNext(emptyTargetOutputPackPayload())
    expect(r.ok).toBe(false)
    expect(r.errors.artifactLines).toBeDefined()
  })

  it('passes with lines', () => {
    const r = validateTargetOutputPackForNext({
      targetStage: 'milestones',
      outputPackKind: 'planning_pack',
      useCustomPackLabel: false,
      packLabel: 'Planning Pack',
      artifactLines: 'One\nTwo',
    })
    expect(r.ok).toBe(true)
  })
})

describe('artifactPackFromTargetPayload', () => {
  it('builds items', () => {
    const p = artifactPackFromTargetPayload(
      {
        targetStage: 'roadmap',
        outputPackKind: 'foundation_pack',
        useCustomPackLabel: false,
        packLabel: 'Foundation Pack',
        artifactLines: 'A\nB',
      },
      'fixed-id',
    )
    expect(p.id).toBe('fixed-id')
    expect(p.items.length).toBe(2)
    expect(p.items[0].status).toBe('draft')
  })
})

describe('formatTargetOutputPackForStepNote', () => {
  it('includes stage and lines', () => {
    const s = formatTargetOutputPackForStepNote({
      targetStage: 'wbes',
      outputPackKind: 'engineering_pack',
      useCustomPackLabel: true,
      packLabel: 'P',
      artifactLines: 'x',
    })
    expect(s).toContain('WBEs')
    expect(s).toContain('P')
  })
})
