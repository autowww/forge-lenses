import { describe, expect, it } from 'vitest'
import {
  effectiveFoundationBriefMarkdown,
  fieldStatusesAfterInterpretationSync,
  foundationBriefDraftHasRenderableContent,
  renderFoundationBriefDraftToMarkdown,
} from './foundationBriefSync'
import { normalizeWizardDomain } from './wizardDomainNormalize'
import { emptyInterpretationPayload } from './interpretationPayload'

describe('foundationBriefDraftHasRenderableContent', () => {
  it('is false when all sections empty', () => {
    expect(foundationBriefDraftHasRenderableContent(emptyInterpretationPayload().foundation_brief_draft)).toBe(false)
  })

  it('is true when any section has text', () => {
    const d = { ...emptyInterpretationPayload().foundation_brief_draft }
    d.problem_statement = { text: 'x', status: 'explicit' }
    expect(foundationBriefDraftHasRenderableContent(d)).toBe(true)
  })
})

describe('renderFoundationBriefDraftToMarkdown', () => {
  it('includes headings for non-empty sections only', () => {
    const d = { ...emptyInterpretationPayload().foundation_brief_draft }
    d.problem_statement = { text: 'P', status: 'inferred' }
    d.scope = { text: 'S', status: 'explicit' }
    const md = renderFoundationBriefDraftToMarkdown(d)
    expect(md).toContain('# Foundation Brief')
    expect(md).toContain('## Problem statement')
    expect(md).toContain('P')
    expect(md).toContain('## Scope')
    expect(md).toContain('S')
    expect(md).not.toContain('## Non-goals')
  })
})

describe('effectiveFoundationBriefMarkdown', () => {
  it('prefers wizard_domain markdown over legacy string', () => {
    const wd = normalizeWizardDomain({})
    wd.foundation_brief.markdown = 'Domain text'
    const pl: Record<string, unknown> = {
      wizard_domain: wd,
      foundation_brief: 'Legacy only',
    }
    expect(effectiveFoundationBriefMarkdown(pl)).toBe('Domain text')
  })

  it('falls back to legacy string when domain markdown empty', () => {
    const wd = normalizeWizardDomain({})
    wd.foundation_brief.markdown = ''
    const pl: Record<string, unknown> = {
      wizard_domain: wd,
      foundation_brief: 'Legacy brief',
    }
    expect(effectiveFoundationBriefMarkdown(pl)).toBe('Legacy brief')
  })
})

describe('fieldStatusesAfterInterpretationSync', () => {
  it('sets fb_* keys and provenance markers', () => {
    const d = { ...emptyInterpretationPayload().foundation_brief_draft }
    d.problem_statement = { text: 'p', status: 'explicit' }
    const out = fieldStatusesAfterInterpretationSync({ llm_foundation_brief: 'inferred' }, d)
    expect(out.fb_problem_statement).toBe('explicit')
    expect(out.foundation_brief_markdown_source).toBe('explicit')
    expect(out.llm_foundation_brief).toBe('unknown')
  })
})
