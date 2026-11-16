import { describe, expect, it } from 'vitest'
import { getNavMeta } from './routeMeta'
import { matchStudioRoute, SR, validateStudioRouteRegistry } from './studioRouteRegistry'

/**
 * Route-level smoke: registry resolves and nav meta is coherent for core Studio paths.
 * Complements React render tests; catches drift when patterns or bundles break.
 *
 * Intentionally excludes **probe** routes (e.g. `/blueprints/wizard/session/:id` — see
 * `StudioRouteDefinition.probeKind` and `listProbeRouteDefinitions`) so product tours and
 * this suite stay on happy-path URLs; probe routes have their own registry tests.
 */
const CORE_PATHS = [
  '/',
  '/overview/charts',
  '/projects',
  '/projects/acme-repo',
  '/projects/acme-repo/charts',
  '/projects/acme-repo/strategy',
  '/plan',
  '/plan/matrix',
  '/timeline',
  '/board',
  '/board/registry',
  '/websites',
  '/websites/browse/acme-site',
  '/blog',
  '/blog/post/example.html',
  '/search',
  '/chat',
  '/tutorials',
  '/workspace-md',
  '/settings/llm',
  '/settings/fleet',
  '/settings/ux-insights',
  '/toolset',
  '/toolset/build.sh',
  '/wbs',
  '/wbs/view',
  '/view/docs/index.html',
  '/view/local-site/acme/',
] as const

describe('core route smoke', () => {
  it('keeps a valid registry while these tests run', () => {
    expect(validateStudioRouteRegistry()).toEqual([])
  })

  it.each(CORE_PATHS)('matchStudioRoute resolves %s', (path) => {
    const m = matchStudioRoute(path, '')
    expect(m.definition?.id).toBeTruthy()
    if (m.definition.id !== SR.fallback) {
      expect(m.definition.pattern || m.definition.planTab).toBeTruthy()
    }
  })

  it.each(CORE_PATHS)('getNavMeta flow+artifacts has aligned breadcrumbs and hrefs for %s', (path) => {
    const f = getNavMeta(path, '', 'flow')
    expect(f.breadcrumbs.length).toBeGreaterThan(0)
    expect(f.hrefs.length).toBe(f.breadcrumbs.length)
    const a = getNavMeta(path, '', 'artifacts')
    expect(a.breadcrumbs.length).toBeGreaterThan(0)
    expect(a.hrefs.length).toBe(a.breadcrumbs.length)
  })

  it('resolves plan today tab', () => {
    const m = matchStudioRoute('/plan', 'tab=today')
    expect(m.definition.id).toContain('today')
  })
})
