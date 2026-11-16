import { describe, expect, it } from 'vitest'
import { emptyWizardDomain } from './wizardDomainNormalize'
import {
  buildMergedArtifactPackAfterGeneration,
  buildRunPlanPreview,
  classifyArtifactPlan,
  runPlanPreviewInputFromShell,
} from './runPlanPreviewEngine'
import { emptyWizardShellState } from './wizardShellState'
import { artifactPackFromTargetPayload } from './targetOutputPackStep'
import type { WizardDomainJson } from './wizardDomainTypes'

function baseInput() {
  const shell = emptyWizardShellState()
  shell.targetOutputPack = {
    ...shell.targetOutputPack,
    artifactLines: 'Artifact A\nArtifact B\n',
  }
  return runPlanPreviewInputFromShell(shell, {
    foundationBriefMarkdownEffective: '# Hello',
    savedWizardDomain: null,
  })
}

describe('classifyArtifactPlan', () => {
  it('marks all lines as create when no saved pack', () => {
    const input = baseInput()
    const c = classifyArtifactPlan(input)
    expect(c.create.length).toBeGreaterThan(0)
    expect(c.update.length).toBe(0)
    expect(c.untouched.length).toBe(0)
  })

  it('classifies matching ready row as untouched under read-only policy', () => {
    const input = baseInput()
    const label = input.targetOutputPack.artifactLines.split('\n').map((l) => l.trim()).filter(Boolean)[0]
    expect(label).toBeTruthy()
    const wd: WizardDomainJson = {
      ...emptyWizardDomain(),
      foundation_brief: { markdown: '# Hello', field_statuses: {} },
      assumption_ledger: [],
      artifact_packs: [
        {
          id: 'pack_test',
          label: 'Pack',
          items: [{ id: 'pack_test-i0', label, status: 'ready' }],
        },
      ],
    }
    const sh = emptyWizardShellState()
    sh.targetOutputPack = {
      ...sh.targetOutputPack,
      artifactLines: 'Artifact A\nArtifact B\n',
    }
    const input2 = runPlanPreviewInputFromShell(sh, {
      foundationBriefMarkdownEffective: '# Hello',
      savedWizardDomain: wd,
    })
    const c = classifyArtifactPlan({
      ...input2,
      autonomyMutation: {
        ...input2.autonomyMutation,
        mutationPolicy: 'read_only_analysis',
        autonomyLevel: 'l0_analyst',
      },
    })
    expect(c.untouched.some((r) => r.label === label)).toBe(true)
    expect(c.create.some((r) => r.label === 'Artifact B')).toBe(true)
  })

  it('creates new label not in previous pack', () => {
    const shell = emptyWizardShellState()
    shell.targetOutputPack = {
      ...shell.targetOutputPack,
      artifactLines: 'Only new line\n',
    }
    const wd: WizardDomainJson = {
      ...emptyWizardDomain(),
      foundation_brief: { markdown: 'x', field_statuses: {} },
      artifact_packs: [
        {
          id: 'pack_x',
          label: 'Old',
          items: [{ id: 'pack_x-i0', label: 'Old artifact', status: 'draft' }],
        },
      ],
    }
    const input = runPlanPreviewInputFromShell(shell, {
      foundationBriefMarkdownEffective: 'x',
      savedWizardDomain: wd,
    })
    const c = classifyArtifactPlan(input)
    expect(c.create.some((r) => r.label.includes('Only new line'))).toBe(true)
  })
})

describe('buildMergedArtifactPackAfterGeneration', () => {
  it('preserves ready row id and status for untouched; drafts create/update', () => {
    const shell = emptyWizardShellState()
    shell.targetOutputPack = {
      ...shell.targetOutputPack,
      artifactLines: 'Stable row\nBrand new row\n',
    }
    shell.autonomyMutation = {
      ...shell.autonomyMutation,
      autonomyLevel: 'l0_analyst',
      mutationPolicy: 'read_only_analysis',
    }
    const wd: WizardDomainJson = {
      ...emptyWizardDomain(),
      foundation_brief: { markdown: 'brief', field_statuses: {} },
      assumption_ledger: [],
      artifact_packs: [
        {
          id: 'pack_keep',
          label: 'Pack',
          items: [{ id: 'stable_id_1', label: 'Stable row', status: 'ready' }],
        },
      ],
    }
    const input = runPlanPreviewInputFromShell(shell, {
      foundationBriefMarkdownEffective: 'brief',
      savedWizardDomain: wd,
    })
    const nextPack = artifactPackFromTargetPayload(shell.targetOutputPack, 'pack_keep')
    const merged = buildMergedArtifactPackAfterGeneration(input, nextPack)
    expect(merged.items.length).toBe(2)
    const stable = merged.items.find((i) => i.label === 'Stable row')
    const created = merged.items.find((i) => i.label === 'Brand new row')
    expect(stable?.id).toBe('stable_id_1')
    expect(stable?.status).toBe('ready')
    expect(created?.status).toBe('draft')
  })
})

describe('buildRunPlanPreview', () => {
  it('includes gates, scope, and blockers for empty foundation when strategy pack', () => {
    const shell = emptyWizardShellState()
    shell.targetOutputPack = {
      ...shell.targetOutputPack,
      outputPackKind: 'strategy_pack',
      artifactLines: 'One\n',
    }
    const input = runPlanPreviewInputFromShell(shell, {
      foundationBriefMarkdownEffective: '',
      savedWizardDomain: null,
    })
    const p = buildRunPlanPreview(input)
    expect(p.reviewGates.length).toBeGreaterThan(0)
    expect(p.scopeBoundaries.length).toBeGreaterThan(0)
    expect(p.blockers.some((b) => b.toLowerCase().includes('foundation'))).toBe(true)
  })

  it('lists open assumptions as blockers', () => {
    const shell = emptyWizardShellState()
    shell.assumptionLedger = [{ id: 'a1', text: 'We assume X', status: 'open' }]
    const input = runPlanPreviewInputFromShell(shell, {
      foundationBriefMarkdownEffective: 'ok',
      savedWizardDomain: null,
    })
    const p = buildRunPlanPreview(input)
    expect(p.blockers.some((b) => b.includes('assume'))).toBe(true)
    expect(p.assumptionsReliedOn.some((a) => a.includes('assume'))).toBe(true)
  })

  it('fills empty run plan from derived draft', () => {
    const shell = emptyWizardShellState()
    shell.mission = { ...shell.mission, title: 'T1' }
    const input = runPlanPreviewInputFromShell(shell, {
      foundationBriefMarkdownEffective: 'fb',
      savedWizardDomain: null,
    })
    const p = buildRunPlanPreview(input)
    expect(p.runPlan.title.length).toBeGreaterThan(0)
    expect(p.runPlan.steps.length).toBeGreaterThan(0)
  })
})
