import { describe, expect, it } from 'vitest'
import {
  getStudioDocumentTitle,
  getStudioNavMeta,
  getStudioTitleTrail,
  matchStudioRoute,
  SR,
  validateStudioRouteRegistry,
} from './studioRouteRegistry'
import { STUDIO_VOCAB } from './studioVisibleCopy'

describe('validateStudioRouteRegistry', () => {
  it('has no structural issues (ids, aliases, duplicate static canonical titles)', () => {
    const issues = validateStudioRouteRegistry()
    expect(issues, JSON.stringify(issues, null, 2)).toEqual([])
  })
})

describe('matchStudioRoute', () => {
  it('treats workspace-md/view as alias of canonical workspace markdown surface', () => {
    const base = matchStudioRoute('/workspace-md', '')
    const view = matchStudioRoute('/workspace-md/view', '')
    expect(base.definition.kind).toBe('canonical')
    expect(view.definition.kind).toBe('alias')
    expect(view.definition.canonicalRouteId).toBe(SR.workspaceMd)
    expect(getStudioNavMeta('/workspace-md', '', 'flow').breadcrumbs).toEqual([
      STUDIO_VOCAB.knowledge,
      STUDIO_VOCAB.workspaceNotes,
    ])
    expect(getStudioNavMeta('/workspace-md', '', 'flow').breadcrumbs).toEqual(
      getStudioNavMeta('/workspace-md/view', '', 'flow').breadcrumbs,
    )
  })

  it('matches /view/docs without splat', () => {
    const m = matchStudioRoute('/view/docs', '')
    expect(m.definition.id).toBe(SR.docsEmbed)
  })

  it('resolves plan query tabs', () => {
    expect(matchStudioRoute('/plan', 'tab=today').definition.id).toBe(SR.planToday)
    expect(matchStudioRoute('/plan', '').definition.id).toBe(SR.planDefault)
  })
})

describe('getStudioDocumentTitle', () => {
  it('includes product suffix and reflects lens-specific breadcrumbs', () => {
    const tFlow = getStudioDocumentTitle('/timeline', '', 'flow')
    expect(tFlow.startsWith('Work › Timeline')).toBe(true)
    expect(tFlow.endsWith(' · Forge Studio')).toBe(true)
    const tArt = getStudioDocumentTitle('/timeline', '', 'artifacts')
    expect(tArt.startsWith('Roadmaps › Timeline')).toBe(true)
  })
})

describe('getStudioTitleTrail', () => {
  it('matches document title body without duplicate tab suffixes', () => {
    const trail = getStudioTitleTrail('/plan', '?tab=today', 'flow')
    expect(trail).toBe('Work › Today')
    expect(getStudioDocumentTitle('/plan', '?tab=today', 'flow')).toBe(`${trail} · Forge Studio`)
  })

  it('appends story id like document title', () => {
    const trail = getStudioTitleTrail('/plan', '?tab=story&id=M1', 'flow')
    expect(trail).toContain('M1')
    expect(trail).toContain('Story')
  })
})
