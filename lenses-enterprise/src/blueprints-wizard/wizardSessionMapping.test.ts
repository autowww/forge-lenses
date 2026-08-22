import { describe, expect, it } from 'vitest'
import type { WizardSessionDocumentJson } from '../api/blueprintsWizard'
import {
  emptyClarificationPayload,
  formatClarificationForStepNote,
} from './clarificationStep'
import {
  emptyContextIntakePayload,
  formatContextIntakeForStepNote,
} from './contextIntakeStep'
import {
  emptyContributionSetupPayload,
  formatContributionSetupForStepNote,
} from './contributionSetupStep'
import { formatMissionForStepNote } from './missionStep'
import { formatAutonomyMutationForStepNote } from './autonomyMutationStep'
import { emptyAutonomyMutationPayload } from './autonomyMutationStep'
import { formatScopeSelectionForStepNote } from './scopeSelectionStep'
import { emptyScopeSelectionPayload } from './scopeSelectionStep'
import { emptyRunPlanPayload, formatRunPlanForStepNote } from './runPlanStep'
import { formatTargetOutputPackForStepNote } from './targetOutputPackStep'
import { emptyTargetOutputPackPayload } from './targetOutputPackStep'
import { emptyInterpretationPayload } from './interpretationPayload'
import { formatUnderstandingForStepNote } from './understandingStep'
import { emptyUnderstandingPayload } from './understandingStep'
import { emptyWizardDomain, normalizeWizardDomain } from './wizardDomainNormalize'
import type { InterpretationFieldStatus } from './wizardDomainTypes'
import { mergeShellIntoWizardDocument, wizardDocumentToShellState } from './wizardSessionMapping'
import type { WizardShellState } from './wizardShellState'

function doc(over: Partial<WizardSessionDocumentJson> = {}): WizardSessionDocumentJson {
  return {
    version: 1,
    updated_at: '2026-01-01T00:00:00Z',
    step_index: 0,
    payload: {},
    ...over,
  }
}

const emptySteps345 = {
  interpretation: emptyInterpretationPayload(),
  understanding: emptyUnderstandingPayload(),
  clarification: emptyClarificationPayload(),
  targetOutputPack: emptyTargetOutputPackPayload(),
  autonomyMutation: emptyAutonomyMutationPayload('single'),
  scopeSelection: emptyScopeSelectionPayload(),
  runPlan: emptyRunPlanPayload(),
}

describe('wizardDocumentToShellState', () => {
  it('maps step_index and stepNotes', () => {
    const d = doc({
      step_index: 3,
      payload: { stepNotes: { '0': 'a', '2': 'c' }, foundation_brief: 'x' },
    })
    const st = wizardDocumentToShellState(d)
    expect(st).toEqual({
      stepIndex: 3,
      stepNotes: { '0': 'a', '2': 'c' },
      mission: { mode: 'start_from_idea', title: '', outcome: '', notes: '' },
      missionType: 'explore',
      contributionSetup: emptyContributionSetupPayload(),
      contributionSetupKind: 'single',
      contextIntake: emptyContextIntakePayload(),
      ...emptySteps345,
      assumptionLedger: [],
      foundationBriefFieldStatuses: {},
      runPlan: expect.objectContaining({ title: '', steps: [] }),
    })
    expect(st.runPlan.id.length).toBeGreaterThan(0)
  })

  it('clamps step index to 12-step range', () => {
    expect(wizardDocumentToShellState(doc({ step_index: 99 })).stepIndex).toBe(11)
  })
})

describe('mergeShellIntoWizardDocument', () => {
  it('preserves foundation_brief and merges notes', () => {
    const base = doc({
      step_index: 1,
      payload: { foundation_brief: 'brief', stepNotes: { '0': 'old' } },
    })
    const shell: WizardShellState = {
      stepIndex: 4,
      stepNotes: { '0': 'a', '4': 'here' },
      mission: { mode: 'start_from_idea' as const, title: 'M', outcome: 'O', notes: '' },
      missionType: 'explore' as const,
      contributionSetup: { deliverable: 'D', landingPlace: 'L', notes: '' },
      contributionSetupKind: 'single' as const,
      contextIntake: {
        roughNotes: 'U',
        sourceFlags: {
          pastedPrompt: false,
          existingDocs: false,
          repoSummary: false,
          ticketsBacklog: false,
        },
        referenceHints: '',
        attachments: [],
      },
      ...emptySteps345,
      assumptionLedger: [],
      foundationBriefFieldStatuses: {},
    }
    const out = mergeShellIntoWizardDocument(base, shell)
    expect(out.step_index).toBe(4)
    expect(out.payload.foundation_brief).toBe('brief')
    expect(out.payload.mission).toEqual({ mode: 'start_from_idea', title: 'M', outcome: 'O', notes: '' })
    expect(out.payload.contributionSetup).toEqual({ deliverable: 'D', landingPlace: 'L', notes: '' })
    expect(out.payload.contextIntake).toEqual(shell.contextIntake)
    const sn = out.payload.stepNotes as Record<string, string>
    expect(sn['0']).toBe(formatMissionForStepNote(shell.mission))
    expect(sn['1']).toBe(formatContributionSetupForStepNote(shell.contributionSetup, shell.contributionSetupKind))
    expect(sn['2']).toBe(formatContextIntakeForStepNote(shell.contextIntake))
    expect(sn['3']).toBe(formatUnderstandingForStepNote(shell.understanding))
    expect(sn['4']).toBe(formatClarificationForStepNote(shell.clarification))
    expect(sn['5']).toBe(formatTargetOutputPackForStepNote(shell.targetOutputPack))
    expect(sn['6']).toBe(formatAutonomyMutationForStepNote(shell.autonomyMutation))
    expect(sn['7']).toBe(formatScopeSelectionForStepNote(shell.scopeSelection))
    expect(sn['8']).toBe(formatRunPlanForStepNote(shell.runPlan))
  })

  it('preserves payload.wizard_domain through merge and sets context_sources', () => {
    const wd = normalizeWizardDomain({ mission_type: 'operate', assumption_ledger: [{ id: 'a', text: 't' }] })
    const base = doc({
      payload: {
        wizard_domain: wd,
        extra: 1,
      } as Record<string, unknown>,
    })
    const shell: WizardShellState = {
      stepIndex: 1,
      stepNotes: {},
      mission: { mode: 'repair_stage' as const, title: 'M', outcome: 'O', notes: '' },
      missionType: 'operate' as const,
      contributionSetup: { deliverable: 'D', landingPlace: 'L', notes: '' },
      contributionSetupKind: 'team' as const,
      contextIntake: {
        roughNotes: '',
        sourceFlags: {
          pastedPrompt: false,
          existingDocs: true,
          repoSummary: true,
          ticketsBacklog: false,
        },
        referenceHints: 'see wiki',
        attachments: [],
      },
      ...emptySteps345,
      assumptionLedger: wd.assumption_ledger,
      foundationBriefFieldStatuses: { ...wd.foundation_brief.field_statuses } as Record<
        string,
        InterpretationFieldStatus
      >,
    }
    const out = mergeShellIntoWizardDocument(base, shell)
    const p = out.payload as Record<string, unknown>
    expect(p.extra).toBe(1)
    const outWd = p.wizard_domain as ReturnType<typeof emptyWizardDomain>
    expect(outWd.mission_type).toBe('operate')
    expect(outWd.assumption_ledger.length).toBe(1)
    expect(outWd.context_sources.sort()).toEqual(['docs', 'repo'].sort())
  })

  it('writes scope_spec, prompt_recipe variables, target_stage, and artifact_packs', () => {
    const base = doc({
      payload: { wizard_domain: normalizeWizardDomain({}) },
    })
    const shell: WizardShellState = {
      stepIndex: 5,
      stepNotes: {},
      mission: { mode: 'start_from_idea' as const, title: 'T', outcome: 'O', notes: '' },
      missionType: 'explore' as const,
      contributionSetup: emptyContributionSetupPayload(),
      contributionSetupKind: 'single' as const,
      contextIntake: emptyContextIntakePayload(),
      interpretation: emptyInterpretationPayload(),
      understanding: { summary: 'We understand the onboarding gap.', knownGaps: 'Metrics unclear.' },
      clarification: {
        openQuestions: 'Who signs off?',
        decisionsNeeded: 'Pick vendor',
        questions: [],
        responses: {},
      },
      targetOutputPack: {
        targetStage: 'milestones',
        outputPackKind: 'planning_pack',
        useCustomPackLabel: true,
        packLabel: 'Onboarding pack',
        artifactLines: 'Run plan\nChecklist',
      },
      autonomyMutation: emptyAutonomyMutationPayload('single'),
      scopeSelection: emptyScopeSelectionPayload(),
      runPlan: emptyRunPlanPayload(),
      assumptionLedger: [],
      foundationBriefFieldStatuses: {},
    }
    const out = mergeShellIntoWizardDocument(base, shell)
    const wd = (out.payload as Record<string, unknown>).wizard_domain as ReturnType<typeof emptyWizardDomain>
    expect(wd.scope_spec.summary).toContain('onboarding gap')
    expect(wd.scope_spec.constraints_note).toContain('Metrics')
    expect(wd.prompt_recipe.variables.clarification_open_questions).toContain('signs off')
    expect(wd.prompt_recipe.variables.clarification_decisions_needed).toContain('vendor')
    expect(wd.target_stage).toBe('milestones')
    expect(wd.artifact_packs.length).toBe(1)
    expect(wd.artifact_packs[0].label).toContain('Onboarding')
    expect(wd.artifact_packs[0].items.length).toBe(2)
  })

  it('applies foundationBriefMarkdownOverride when provided', () => {
    const base = doc({
      payload: { wizard_domain: normalizeWizardDomain({}) },
    })
    const shell: WizardShellState = {
      stepIndex: 0,
      stepNotes: {},
      mission: { mode: 'start_from_idea' as const, title: '', outcome: '', notes: '' },
      missionType: 'explore' as const,
      contributionSetup: emptyContributionSetupPayload(),
      contributionSetupKind: 'single' as const,
      contextIntake: emptyContextIntakePayload(),
      ...emptySteps345,
      assumptionLedger: [],
      foundationBriefFieldStatuses: {},
    }
    const out = mergeShellIntoWizardDocument(base, shell, {
      foundationBriefMarkdownOverride: '# Hello\n\nFrom sync.',
    })
    const wd = (out.payload as Record<string, unknown>).wizard_domain as ReturnType<typeof emptyWizardDomain>
    expect(wd.foundation_brief.markdown).toContain('From sync.')
  })

  it('at step 9+ merges artifact packs incrementally (untouched ready rows keep id and status)', () => {
    const wd = normalizeWizardDomain({
      ...emptyWizardDomain(),
      foundation_brief: { markdown: 'shared-brief', field_statuses: {} },
      artifact_packs: [
        {
          id: 'pack_merge',
          label: 'Primary',
          items: [{ id: 'keep-ready-id', label: 'Line A', status: 'ready' }],
        },
      ],
    })
    const base = doc({
      payload: { wizard_domain: wd },
    })
    const shell: WizardShellState = {
      stepIndex: 9,
      stepNotes: {},
      mission: { mode: 'start_from_idea' as const, title: 'T', outcome: 'O', notes: '' },
      missionType: 'explore' as const,
      contributionSetup: emptyContributionSetupPayload(),
      contributionSetupKind: 'single' as const,
      contextIntake: emptyContextIntakePayload(),
      interpretation: emptyInterpretationPayload(),
      understanding: { summary: 'u', knownGaps: '' },
      clarification: {
        openQuestions: '',
        decisionsNeeded: '',
        questions: [],
        responses: {},
      },
      targetOutputPack: {
        targetStage: 'idea',
        outputPackKind: 'foundation_pack',
        useCustomPackLabel: false,
        packLabel: 'Foundation Pack',
        artifactLines: 'Line A\nLine B\n',
      },
      autonomyMutation: {
        autonomyLevel: 'l0_analyst',
        mutationPolicy: 'read_only_analysis',
        advancedOverride: false,
        guardrailAcknowledged: false,
      },
      scopeSelection: emptyScopeSelectionPayload(),
      runPlan: emptyRunPlanPayload(),
      assumptionLedger: [],
      foundationBriefFieldStatuses: {},
    }
    const out = mergeShellIntoWizardDocument(base, shell)
    const outWd = (out.payload as Record<string, unknown>).wizard_domain as ReturnType<typeof emptyWizardDomain>
    expect(outWd.artifact_packs.length).toBe(1)
    const items = outWd.artifact_packs[0].items
    expect(items.length).toBe(2)
    const lineA = items.find((i) => i.label === 'Line A')
    const lineB = items.find((i) => i.label === 'Line B')
    expect(lineA?.id).toBe('keep-ready-id')
    expect(lineA?.status).toBe('ready')
    expect(lineB?.status).toBe('draft')
  })

  it('at step 8 still replaces artifact pack from target lines (full materialization)', () => {
    const wd = normalizeWizardDomain({
      ...emptyWizardDomain(),
      foundation_brief: { markdown: 'shared-brief', field_statuses: {} },
      artifact_packs: [
        {
          id: 'pack_old',
          label: 'Primary',
          items: [{ id: 'old-id', label: 'Line A', status: 'ready' }],
        },
      ],
    })
    const base = doc({
      payload: { wizard_domain: wd },
    })
    const shell: WizardShellState = {
      stepIndex: 8,
      stepNotes: {},
      mission: { mode: 'start_from_idea' as const, title: 'T', outcome: 'O', notes: '' },
      missionType: 'explore' as const,
      contributionSetup: emptyContributionSetupPayload(),
      contributionSetupKind: 'single' as const,
      contextIntake: emptyContextIntakePayload(),
      interpretation: emptyInterpretationPayload(),
      understanding: { summary: 'u', knownGaps: '' },
      clarification: {
        openQuestions: '',
        decisionsNeeded: '',
        questions: [],
        responses: {},
      },
      targetOutputPack: {
        targetStage: 'idea',
        outputPackKind: 'foundation_pack',
        useCustomPackLabel: false,
        packLabel: 'Foundation Pack',
        artifactLines: 'Line A\nLine B\n',
      },
      autonomyMutation: {
        autonomyLevel: 'l0_analyst',
        mutationPolicy: 'read_only_analysis',
        advancedOverride: false,
        guardrailAcknowledged: false,
      },
      scopeSelection: emptyScopeSelectionPayload(),
      runPlan: emptyRunPlanPayload(),
      assumptionLedger: [],
      foundationBriefFieldStatuses: {},
    }
    const out = mergeShellIntoWizardDocument(base, shell)
    const outWd = (out.payload as Record<string, unknown>).wizard_domain as ReturnType<typeof emptyWizardDomain>
    const items = outWd.artifact_packs[0].items
    const lineA = items.find((i) => i.label === 'Line A')
    expect(lineA?.id).not.toBe('old-id')
    expect(lineA?.status).toBe('draft')
  })

  it('updates legacy payload.foundation_brief string when override is set', () => {
    const base = doc({
      payload: {
        wizard_domain: normalizeWizardDomain({}),
        foundation_brief: 'old legacy',
      } as Record<string, unknown>,
    })
    const shell: WizardShellState = {
      stepIndex: 0,
      stepNotes: {},
      mission: { mode: 'start_from_idea' as const, title: '', outcome: '', notes: '' },
      missionType: 'explore' as const,
      contributionSetup: emptyContributionSetupPayload(),
      contributionSetupKind: 'single' as const,
      contextIntake: emptyContextIntakePayload(),
      ...emptySteps345,
      assumptionLedger: [],
      foundationBriefFieldStatuses: {},
    }
    const out = mergeShellIntoWizardDocument(base, shell, {
      foundationBriefMarkdownOverride: 'new unified',
    })
    const p = out.payload as Record<string, unknown>
    expect(p.foundation_brief).toBe('new unified')
  })
})
