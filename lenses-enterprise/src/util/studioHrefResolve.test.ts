import { describe, expect, it, vi } from 'vitest'
import { expandRelativeStudioHref, normalizeStudioAppHref, stripStudioUrlPath } from './studioHrefResolve'

describe('stripStudioUrlPath', () => {
  it('strips /studio prefix', () => {
    expect(stripStudioUrlPath('/studio/plan')).toBe('/plan')
    expect(stripStudioUrlPath('/studio')).toBe('/')
  })
})

describe('expandRelativeStudioHref', () => {
  it('resolves plan? to site-root path (never /…/wbs/plan)', () => {
    vi.stubGlobal('window', {
      location: { origin: 'http://127.0.0.1:8080' },
    })
    const out = expandRelativeStudioHref('plan?tab=story&id=1')
    expect(out.endsWith('plan?tab=story&id=1')).toBe(true)
    expect(out).not.toContain('/wbs/')
    vi.unstubAllGlobals()
  })
})

describe('normalizeStudioAppHref', () => {
  it('maps relative story link to /plan for router', () => {
    vi.stubGlobal('window', {
      location: { origin: 'http://127.0.0.1:8080' },
    })
    const o = 'http://127.0.0.1:8080'
    expect(normalizeStudioAppHref('plan?tab=story&wbs_p=a&id=b', o)).toBe('/plan?tab=story&wbs_p=a&id=b')
    vi.unstubAllGlobals()
  })
})
