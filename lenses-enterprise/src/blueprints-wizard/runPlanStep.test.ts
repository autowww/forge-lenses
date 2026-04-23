import { describe, expect, it } from 'vitest'
import { emptyWizardDomain, normalizeRunPlan } from './wizardDomainNormalize'
import {
  deriveDraftRunPlan,
  deriveDraftRunPlanFromShell,
  emptyRunPlanPayload,
  validateRunPlanForNext,
} from './runPlanStep'
import type { WizardShellState } from './wizardShellState'
import { emptyWizardShellState } from './wizardShellState'

describe('deriveDraftRunPlan', () => {
  it('builds a titled plan with multiple steps', () => {
    const spec = emptyWizardDomain().scope_spec
    spec.summary = 'Ship onboarding improvements.'
    spec.constraints_note = 'Metrics TBD.'
    spec.scope_boundary = 'milestone'
    spec.milestone_ref = 'M3'
    const p = deriveDraftRunPlan({
      missionTitle: 'Acme Portal',
      targetStage: 'milestones',
      outputPackKind: 'planning_pack',
      scopeSpec: spec,
    })
    expect(p.title).toContain('Acme Portal')
    expect(p.title).toContain('Milestones')
    expect(p.steps.length).toBeGreaterThanOrEqual(4)
    expect(p.steps[0].title.length).toBeGreaterThan(0)
  })
})

describe('deriveDraftRunPlanFromShell', () => {
  it('uses mission, target pack, and merged scope', () => {
    const base = emptyWizardShellState()
    const shell: WizardShellState = {
      ...base,
      mission: { ...base.mission, title: 'Q1' },
      targetOutputPack: {
        ...base.targetOutputPack,
        targetStage: 'roadmap',
        outputPackKind: 'strategy_pack',
      },
      understanding: { summary: 'We need a north-star.', knownGaps: '' },
      scopeSelection: { ...base.scopeSelection, scopeBoundary: 'full_plan' },
    }
    const p = deriveDraftRunPlanFromShell(shell)
    expect(normalizeRunPlan(p).steps.length).toBeGreaterThan(0)
    expect(p.title).toContain('Q1')
  })
})

describe('validateRunPlanForNext', () => {
  it('requires title and step titles', () => {
    expect(validateRunPlanForNext(emptyRunPlanPayload()).ok).toBe(false)
    const ok = validateRunPlanForNext(
      normalizeRunPlan({
        title: 'Plan',
        steps: [{ id: 'a', title: 'One', detail: '' }],
      }),
    )
    expect(ok.ok).toBe(true)
  })
})
