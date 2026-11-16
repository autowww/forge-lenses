import { describe, expect, it } from 'vitest'
import {
  getBackTarget,
  getBreadcrumbSegments,
  getNavMeta,
  suggestNavModeFromPath,
} from './routeMeta'
import { validateStudioRouteRegistry } from './studioRouteRegistry'
import { STUDIO_VOCAB } from './studioVisibleCopy'

describe('route registry guard', () => {
  it('stays valid when routeMeta tests run', () => {
    expect(validateStudioRouteRegistry()).toEqual([])
  })
})

describe('getNavMeta', () => {
  it('resolves home', () => {
    const h = getNavMeta('/', '', 'flow')
    expect(h.groupId).toBe('home')
    expect(h.breadcrumbs).toEqual(['Home', 'Overview'])
    expect(h.hrefs).toHaveLength(h.breadcrumbs.length)
  })

  it('resolves plan today tab under Work for both lenses', () => {
    const f = getNavMeta('/plan', 'tab=today', 'flow')
    expect(f.groupId).toBe('work')
    expect(f.breadcrumbs[0]).toBe('Work')

    const a = getNavMeta('/plan', 'tab=today', 'artifacts')
    expect(a.groupId).toBe('work')
  })

  it('resolves project strategy paths', () => {
    const f = getNavMeta('/projects/foo/strategy', '', 'flow')
    expect(f.groupId).toBe('projects')
    expect(f.breadcrumbs).toContain(STUDIO_VOCAB.architectureStrategy)
    const a = getNavMeta('/projects/foo/strategy', '', 'artifacts')
    expect(a.groupId).toBe('projects')
  })

  it('places search and chat under Tools in breadcrumbs (global header utilities), not Knowledge', () => {
    const s = getNavMeta('/search', 'q=test', 'flow')
    expect(s.groupId).toBe('home')
    expect(s.breadcrumbs[0]).toBe(STUDIO_VOCAB.studioTools)
    expect(s.breadcrumbs).toContain(STUDIO_VOCAB.search)
    const c = getNavMeta('/chat', '', 'artifacts')
    expect(c.groupId).toBe('home')
    expect(c.breadcrumbs[0]).toBe(STUDIO_VOCAB.studioTools)
    expect(c.breadcrumbs).toContain(STUDIO_VOCAB.llmChat)
  })

  it('places workspace notes under Knowledge', () => {
    const m = getNavMeta('/workspace-md', '', 'flow')
    expect(m.groupId).toBe('knowledge')
    expect(m.breadcrumbs[0]).toBe(STUDIO_VOCAB.knowledge)
    expect(m.breadcrumbs).toContain(STUDIO_VOCAB.workspaceNotes)
  })

  it('maps timeline to Work for both lenses', () => {
    expect(getNavMeta('/timeline', '', 'flow').groupId).toBe('work')
    expect(getNavMeta('/timeline', '', 'artifacts').groupId).toBe('work')
  })

  it('resolves blog routes under Publish', () => {
    expect(getNavMeta('/blog', '', 'flow').groupId).toBe('publish')
    expect(getNavMeta('/blog/post/foo.html', '', 'artifacts').groupId).toBe('publish')
  })

  it('keeps hrefs aligned with breadcrumbs', () => {
    const paths = [
      '/',
      '/projects',
      '/projects/x',
      '/projects/x/charts',
      '/plan',
      '/wbs/view',
      '/search',
      '/chat',
      '/workspace-md',
      '/tutorials',
      '/settings/ux-insights',
      '/governance/connectors',
      '/governance/audit',
      '/knowledge/methodology/evidence',
      '/knowledge/methodology/decisions',
      '/knowledge/methodology/readiness',
      '/knowledge/methodology/record/ogs:demo:b2:psp',
      '/knowledge/agentic-bridge',
    ]
    for (const p of paths) {
      const m = getNavMeta(p, p === '/plan' ? 'tab=today' : '', 'flow')
      expect(m.hrefs.length).toBe(m.breadcrumbs.length)
    }
  })
})

describe('getBackTarget & getBreadcrumbSegments', () => {
  it('returns parent path for nested project route', () => {
    expect(getBackTarget('/projects/myrepo/charts', '', 'flow')).toBe('/projects')
  })

  it('maps segments with hrefs for charts overview', () => {
    const s = getBreadcrumbSegments('/overview/charts', '', 'flow')
    expect(s[0]).toEqual({ label: STUDIO_VOCAB.adminInspect, href: null })
    expect(s[1]).toEqual({ label: STUDIO_VOCAB.advancedReporting, href: null })
  })
})

describe('suggestNavModeFromPath', () => {
  it('does not infer lens from path (shared routes use context + primary nav)', () => {
    expect(suggestNavModeFromPath('/plan')).toBeNull()
    expect(suggestNavModeFromPath('/timeline')).toBeNull()
    expect(suggestNavModeFromPath('/board')).toBeNull()
    expect(suggestNavModeFromPath('/search')).toBeNull()
  })
})
