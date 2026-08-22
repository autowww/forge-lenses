import { describe, expect, it } from 'vitest'
import { validateStudioRouteRegistry } from './studioRouteRegistry'
import { STUDIO_GLOSSARY, STUDIO_VOCAB } from './studioVisibleCopy'

describe('studioVisibleCopy', () => {
  it('keeps glossary entries non-empty', () => {
    for (const [k, v] of Object.entries(STUDIO_GLOSSARY)) {
      expect(v.title.trim(), k).toBeTruthy()
      expect(v.short.trim(), k).toBeTruthy()
      expect(v.long.trim(), k).toBeTruthy()
    }
  })

  it('aligns core plan vocabulary with a valid route registry', () => {
    const issues = validateStudioRouteRegistry()
    expect(issues, JSON.stringify(issues)).toEqual([])
    expect(STUDIO_VOCAB.plan).toBe('Plan')
    expect(STUDIO_VOCAB.story).toBe('Story')
    expect(STUDIO_VOCAB.sources).toBe('Sources')
    expect(STUDIO_VOCAB.today).toBe('Today')
    expect(STUDIO_VOCAB.workspaceNotes).toBe('Workspace notes')
  })

  it('exposes story glossary for UI tooltips', () => {
    expect(STUDIO_GLOSSARY.story.short.toLowerCase()).toContain('plan')
  })
})
