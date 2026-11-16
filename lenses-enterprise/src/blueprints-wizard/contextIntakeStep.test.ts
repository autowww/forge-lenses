import { describe, expect, it } from 'vitest'
import {
  contextSourcesForWizardDomain,
  deriveContextSourcesFromIntake,
  emptyContextIntakePayload,
  formatContextIntakeForStepNote,
  parseContextIntakeFromPayload,
  validateContextIntakeForNext,
} from './contextIntakeStep'

describe('validateContextIntakeForNext', () => {
  it('requires rough notes or flags plus references', () => {
    const r = validateContextIntakeForNext(emptyContextIntakePayload())
    expect(r.ok).toBe(false)
    expect(r.errors.roughNotes).toBeDefined()
  })

  it('passes with rough notes only', () => {
    const r = validateContextIntakeForNext({
      ...emptyContextIntakePayload(),
      roughNotes: 'Something',
    })
    expect(r.ok).toBe(true)
  })

  it('passes with flags and reference hints', () => {
    const r = validateContextIntakeForNext({
      roughNotes: '',
      sourceFlags: { ...emptyContextIntakePayload().sourceFlags, ticketsBacklog: true },
      referenceHints: 'JIRA-1',
      attachments: [],
    })
    expect(r.ok).toBe(true)
  })
})

describe('parseContextIntakeFromPayload', () => {
  it('reads v2 shape', () => {
    const x = parseContextIntakeFromPayload({
      contextIntake: {
        roughNotes: 'R',
        referenceHints: 'T-1',
        sourceFlags: { pastedPrompt: true, existingDocs: false, repoSummary: false, ticketsBacklog: true },
        attachments: [],
      },
    })
    expect(x.roughNotes).toBe('R')
    expect(x.sourceFlags.ticketsBacklog).toBe(true)
  })

  it('migrates legacy sources and summary', () => {
    const x = parseContextIntakeFromPayload({
      contextIntake: { sources: 'Repo A', summary: 'Important', notes: '' },
    })
    expect(x.roughNotes).toContain('Repo A')
    expect(x.roughNotes).toContain('Important')
  })
})

describe('deriveContextSourcesFromIntake', () => {
  it('maps flags to domain sources', () => {
    const x = {
      ...emptyContextIntakePayload(),
      sourceFlags: {
        pastedPrompt: true,
        existingDocs: true,
        repoSummary: true,
        ticketsBacklog: false,
      },
    }
    expect(deriveContextSourcesFromIntake(x).sort()).toEqual(['docs', 'other', 'repo'].sort())
  })
})

describe('contextSourcesForWizardDomain', () => {
  it('uses rough notes when no flags', () => {
    const prev = ['stakeholders' as const]
    expect(
      contextSourcesForWizardDomain(
        { ...emptyContextIntakePayload(), roughNotes: 'text' },
        prev,
      ),
    ).toEqual(['other'])
  })
})

describe('formatContextIntakeForStepNote', () => {
  it('joins parts', () => {
    const s = formatContextIntakeForStepNote({
      roughNotes: 'R',
      sourceFlags: {
        pastedPrompt: false,
        existingDocs: true,
        repoSummary: false,
        ticketsBacklog: false,
      },
      referenceHints: 'H',
      attachments: [{ kind: 'wbs', label: 'W', ref: 'p/wbs.md' }],
    })
    expect(s).toContain('Rough notes: R')
    expect(s).toContain('References: H')
    expect(s).toContain('wbs.md')
  })
})
