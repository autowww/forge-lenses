import {
  clampContextIntakePayload,
  emptyContextIntakePayload,
  parseContextIntakeFromPayload,
  type ContextIntakePayloadV1,
} from './contextIntakeStep'
import {
  clampContributionSetupPayload,
  emptyContributionSetupPayload,
  type ContributionSetupPayloadV1,
} from './contributionSetupStep'
import {
  clampMissionPayload,
  emptyMissionPayload,
  hasExplicitMissionMode,
  missionModeToMissionType,
  missionTypeToMissionMode,
  MISSION_MODES,
  type MissionMode,
  type MissionPayloadV1,
} from './missionStep'
import { clampInterpretationPayload } from './interpretationPayload'
import { emptyRunPlanPayload } from './runPlanStep'
import type { WizardShellState } from './wizardShellState'
import type { ContributionSetupKind, MissionType, WizardDomainJson } from './wizardDomainTypes'
import { emptyWizardDomain, normalizeWizardDomain } from './wizardDomainNormalize'
import type { WizardSessionDocumentJson } from '../api/blueprintsWizard'
import { wizardDocumentToShellState } from './wizardSessionMapping'

/** Local / session-tab persistence when the server wizard API is off or unreachable. Server sync uses `api/blueprintsWizard` and `wizardSessionMapping` in `BlueprintsWizardSessionPage`. */

/** Shell state plus optional typed domain (`payload.wizard_domain` mirror) for local drafts. */
export type WizardPersistedState = WizardShellState & {
  wizardDomain?: WizardDomainJson
}

/** Local / session-tab persistence for the wizard shell (no server). */
export interface WizardShellPersistence {
  load(): WizardPersistedState | null
  save(state: WizardPersistedState): void
  clear(): void
}

export const WIZARD_SHELL_STORAGE_KEY = 'lenses.studio.blueprintsWizard.shell.v2'

export function createSessionStorageWizardPersistence(
  storageKey: string = WIZARD_SHELL_STORAGE_KEY,
  storage: Storage = typeof sessionStorage !== 'undefined' ? sessionStorage : ({} as Storage),
): WizardShellPersistence {
  return {
    load(): WizardPersistedState | null {
      try {
        const raw = storage.getItem(storageKey)
        if (!raw) return null
        const parsed = JSON.parse(raw) as unknown
        if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return null
        const o = parsed as Record<string, unknown>
        const stepIndex = o.stepIndex
        const stepNotes = o.stepNotes
        if (typeof stepIndex !== 'number' || stepNotes === null || typeof stepNotes !== 'object') {
          return null
        }
        const notes: Record<string, string> = {}
        for (const [k, v] of Object.entries(stepNotes as Record<string, unknown>)) {
          if (typeof v === 'string') notes[k] = v
        }
        const missionRaw = o.mission
        let mission: MissionPayloadV1 = emptyMissionPayload()
        if (missionRaw && typeof missionRaw === 'object' && !Array.isArray(missionRaw)) {
          const mr = missionRaw as Record<string, unknown>
          const rawMode = mr.mode
          const mode: MissionMode =
            typeof rawMode === 'string' && (MISSION_MODES as readonly string[]).includes(rawMode)
              ? (rawMode as MissionMode)
              : 'start_from_idea'
          mission = clampMissionPayload({
            mode,
            title: typeof mr.title === 'string' ? mr.title : '',
            outcome: typeof mr.outcome === 'string' ? mr.outcome : '',
            notes: typeof mr.notes === 'string' ? mr.notes : '',
          })
        }
        const csRaw = o.contributionSetup
        let contributionSetup: ContributionSetupPayloadV1 = emptyContributionSetupPayload()
        if (csRaw && typeof csRaw === 'object' && !Array.isArray(csRaw)) {
          const cr = csRaw as Record<string, unknown>
          contributionSetup = clampContributionSetupPayload({
            deliverable: typeof cr.deliverable === 'string' ? cr.deliverable : '',
            landingPlace: typeof cr.landingPlace === 'string' ? cr.landingPlace : '',
            notes: typeof cr.notes === 'string' ? cr.notes : '',
          })
        }
        const cxRaw = o.contextIntake
        let contextIntake: ContextIntakePayloadV1 = emptyContextIntakePayload()
        if (cxRaw && typeof cxRaw === 'object' && !Array.isArray(cxRaw)) {
          contextIntake = clampContextIntakePayload(
            parseContextIntakeFromPayload({ contextIntake: cxRaw as Record<string, unknown> }),
          )
        }
        const wdRaw = o.wizardDomain ?? o.persistedWizardDomain
        const baseWd =
          wdRaw !== null && wdRaw !== undefined ? normalizeWizardDomain(wdRaw) : emptyWizardDomain()
        if (
          missionRaw &&
          typeof missionRaw === 'object' &&
          !Array.isArray(missionRaw) &&
          !hasExplicitMissionMode({ mission: missionRaw as Record<string, unknown> })
        ) {
          mission = {
            ...mission,
            mode: missionTypeToMissionMode(baseWd.mission_type as MissionType),
          }
        }
        const missionType = missionModeToMissionType(mission.mode)
        const contributionSetupKind = (typeof o.contributionSetupKind === 'string'
          ? o.contributionSetupKind
          : baseWd.contribution_setup_kind) as ContributionSetupKind
        const wizardDomain = normalizeWizardDomain({
          ...baseWd,
          mission_type: missionType,
          contribution_setup_kind: contributionSetupKind,
        })
        const fakeDoc: WizardSessionDocumentJson = {
          version: 1,
          updated_at: '',
          step_index: stepIndex,
          payload: {
            stepNotes: notes,
            mission,
            contributionSetup,
            contextIntake,
            ...(typeof o.interpretation === 'object' &&
            o.interpretation !== null &&
            !Array.isArray(o.interpretation)
              ? { interpretation: o.interpretation as Record<string, unknown> }
              : {}),
            understanding: o.understanding,
            clarification: o.clarification,
            targetOutputPack: o.targetOutputPack,
            wizard_domain: wizardDomain,
          },
        }
        const shell = wizardDocumentToShellState(fakeDoc)
        return {
          ...shell,
          persistedWizardDomain: wizardDomain,
          wizardDomain,
        }
      } catch {
        return null
      }
    },
    save(state: WizardPersistedState): void {
      try {
        storage.setItem(storageKey, JSON.stringify(state))
      } catch {
        /* quota or private mode */
      }
    },
    clear(): void {
      try {
        storage.removeItem(storageKey)
      } catch {
        /* ignore */
      }
    },
  }
}

export function createInMemoryWizardPersistence(): WizardShellPersistence {
  let memory: WizardPersistedState | null = null
  return {
    load(): WizardPersistedState | null {
      return memory
    },
    save(state: WizardPersistedState): void {
      memory = {
        ...state,
        stepNotes: { ...state.stepNotes },
        mission: { ...state.mission },
        contributionSetup: { ...state.contributionSetup },
        contextIntake: { ...state.contextIntake },
        interpretation: clampInterpretationPayload(state.interpretation),
        understanding: { ...state.understanding },
        clarification: { ...state.clarification },
        targetOutputPack: { ...state.targetOutputPack },
        autonomyMutation: { ...state.autonomyMutation },
        scopeSelection: { ...state.scopeSelection },
        runPlan: state.runPlan
          ? { ...state.runPlan, steps: state.runPlan.steps.map((s) => ({ ...s })) }
          : emptyRunPlanPayload(),
        missionType: state.missionType,
        contributionSetupKind: state.contributionSetupKind,
        assumptionLedger: state.assumptionLedger.map((e) => ({ ...e })),
        foundationBriefFieldStatuses: { ...state.foundationBriefFieldStatuses },
        ...(state.persistedWizardDomain !== undefined
          ? { persistedWizardDomain: state.persistedWizardDomain }
          : {}),
        ...(state.wizardDomain !== undefined ? { wizardDomain: state.wizardDomain } : {}),
      }
    },
    clear(): void {
      memory = null
    },
  }
}
