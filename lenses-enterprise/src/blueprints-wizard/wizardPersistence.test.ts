import { describe, expect, it, beforeEach } from 'vitest'
import { emptyContributionSetupPayload } from './contributionSetupStep'
import { emptyClarificationPayload } from './clarificationStep'
import { emptyContextIntakePayload } from './contextIntakeStep'
import { emptyMissionPayload } from './missionStep'
import { emptyAutonomyMutationPayload } from './autonomyMutationStep'
import { emptyScopeSelectionPayload } from './scopeSelectionStep'
import { emptyTargetOutputPackPayload } from './targetOutputPackStep'
import { emptyRunPlanPayload } from './runPlanStep'
import { emptyInterpretationPayload } from './interpretationPayload'
import { emptyUnderstandingPayload } from './understandingStep'
import { emptyWizardDomain, normalizeWizardDomain } from './wizardDomainNormalize'
import {
  WIZARD_SHELL_STORAGE_KEY,
  createInMemoryWizardPersistence,
  createSessionStorageWizardPersistence,
} from './wizardPersistence'

describe('createInMemoryWizardPersistence', () => {
  it('round-trips state', () => {
    const p = createInMemoryWizardPersistence()
    expect(p.load()).toBeNull()
    p.save({
      stepIndex: 2,
      stepNotes: { '0': 'a', '1': 'b' },
      mission: { mode: 'start_from_idea', title: 'T', outcome: 'O', notes: 'N' },
      missionType: 'explore',
      contributionSetup: { deliverable: 'D', landingPlace: 'L', notes: '' },
      contributionSetupKind: 'single',
      contextIntake: {
        roughNotes: 'src\n\nsum',
        sourceFlags: emptyContextIntakePayload().sourceFlags,
        referenceHints: '',
        attachments: [],
      },
      interpretation: emptyInterpretationPayload(),
      understanding: emptyUnderstandingPayload(),
      clarification: emptyClarificationPayload(),
      targetOutputPack: emptyTargetOutputPackPayload(),
      autonomyMutation: emptyAutonomyMutationPayload('single'),
      scopeSelection: emptyScopeSelectionPayload(),
      runPlan: emptyRunPlanPayload(),
      assumptionLedger: [],
      foundationBriefFieldStatuses: {},
    })
    const loaded = p.load()
    expect(loaded?.stepIndex).toBe(2)
    expect(loaded?.stepNotes).toEqual({ '0': 'a', '1': 'b' })
    expect(loaded?.mission).toEqual({ mode: 'start_from_idea', title: 'T', outcome: 'O', notes: 'N' })
    expect(loaded?.missionType).toBe('explore')
    expect(loaded?.contributionSetupKind).toBe('single')
    expect(loaded?.contributionSetup).toEqual({ deliverable: 'D', landingPlace: 'L', notes: '' })
    expect(loaded?.contextIntake).toEqual({
      roughNotes: 'src\n\nsum',
      sourceFlags: emptyContextIntakePayload().sourceFlags,
      referenceHints: '',
      attachments: [],
    })
    p.clear()
    expect(p.load()).toBeNull()
  })

  it('round-trips optional wizardDomain', () => {
    const p = createInMemoryWizardPersistence()
    const wd = normalizeWizardDomain({ mission_type: 'deliver' })
    p.save({
      stepIndex: 0,
      stepNotes: {},
      mission: emptyMissionPayload(),
      missionType: 'deliver',
      contributionSetup: emptyContributionSetupPayload(),
      contributionSetupKind: 'single',
      contextIntake: emptyContextIntakePayload(),
      interpretation: emptyInterpretationPayload(),
      understanding: emptyUnderstandingPayload(),
      clarification: emptyClarificationPayload(),
      targetOutputPack: emptyTargetOutputPackPayload(),
      autonomyMutation: emptyAutonomyMutationPayload('single'),
      scopeSelection: emptyScopeSelectionPayload(),
      runPlan: emptyRunPlanPayload(),
      assumptionLedger: [],
      foundationBriefFieldStatuses: {},
      wizardDomain: wd,
    })
    const loaded = p.load()
    expect(loaded?.wizardDomain?.mission_type).toBe('deliver')
    expect(loaded?.wizardDomain?.schema_version).toBe(emptyWizardDomain().schema_version)
  })
})

describe('createSessionStorageWizardPersistence', () => {
  beforeEach(() => {
    sessionStorage.removeItem(WIZARD_SHELL_STORAGE_KEY)
  })

  it('persists under default key', () => {
    const p = createSessionStorageWizardPersistence()
    p.save({
      stepIndex: 3,
      stepNotes: { '2': 'x' },
      mission: emptyMissionPayload(),
      missionType: 'explore',
      contributionSetup: emptyContributionSetupPayload(),
      contributionSetupKind: 'single',
      contextIntake: emptyContextIntakePayload(),
      interpretation: emptyInterpretationPayload(),
      understanding: emptyUnderstandingPayload(),
      clarification: emptyClarificationPayload(),
      targetOutputPack: emptyTargetOutputPackPayload(),
      autonomyMutation: emptyAutonomyMutationPayload('single'),
      scopeSelection: emptyScopeSelectionPayload(),
      runPlan: emptyRunPlanPayload(),
      assumptionLedger: [],
      foundationBriefFieldStatuses: {},
    })
    const p2 = createSessionStorageWizardPersistence()
    const loaded = p2.load()
    expect(loaded?.stepIndex).toBe(3)
    expect(loaded?.stepNotes).toEqual({ '2': 'x' })
    expect(loaded?.mission).toEqual(emptyMissionPayload())
    expect(loaded?.missionType).toBe('explore')
    expect(loaded?.contributionSetupKind).toBe('single')
    expect(loaded?.contributionSetup).toEqual(emptyContributionSetupPayload())
    expect(loaded?.contextIntake).toEqual(emptyContextIntakePayload())
    expect(loaded?.wizardDomain?.mission_type).toBe('explore')
  })

  it('returns null for invalid JSON', () => {
    sessionStorage.setItem(WIZARD_SHELL_STORAGE_KEY, '{')
    const p = createSessionStorageWizardPersistence()
    expect(p.load()).toBeNull()
  })
})
