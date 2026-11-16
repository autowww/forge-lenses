import { describe, expect, it } from 'vitest'
import { hrefToStudioRouterTo, isSpaHandledPathname } from './studioSameOriginLink'

const O = 'http://127.0.0.1:8080'

describe('isSpaHandledPathname', () => {
  it('allows workspace-md and view', () => {
    expect(isSpaHandledPathname('/workspace-md/view')).toBe(true)
    expect(isSpaHandledPathname('/view/docs/x.html')).toBe(true)
  })
  it('allows methodology and governance Studio routes', () => {
    expect(isSpaHandledPathname('/knowledge/methodology/evidence')).toBe(true)
    expect(isSpaHandledPathname('/governance/connectors')).toBe(true)
  })
  it('rejects classic-only paths', () => {
    expect(isSpaHandledPathname('/roadmaps/summary')).toBe(false)
  })
})

describe('hrefToStudioRouterTo', () => {
  it('maps root /plan and /docs', () => {
    expect(hrefToStudioRouterTo('/plan?tab=story&id=a', O)).toBe('/plan?tab=story&id=a')
    expect(hrefToStudioRouterTo('/docs/x.html', O)).toBe('/view/docs/x.html')
  })

  it('maps knowledge and governance hrefs', () => {
    expect(hrefToStudioRouterTo('/knowledge/methodology/readiness', O)).toBe(
      '/knowledge/methodology/readiness',
    )
    expect(hrefToStudioRouterTo('/governance/audit', O)).toBe('/governance/audit')
  })

  it('maps classic workspace-md view URL', () => {
    expect(hrefToStudioRouterTo('/workspace-md/view?p=forge%2Fcharge.md', O)).toBe(
      '/workspace-md/view?p=forge%2Fcharge.md',
    )
  })

  it('strips /studio prefix on href', () => {
    expect(hrefToStudioRouterTo(`${O}/studio/plan?x=1`, O)).toBe('/plan?x=1')
  })

  it('returns null for api and unknown paths', () => {
    expect(hrefToStudioRouterTo('/api/foo', O)).toBe(null)
    expect(hrefToStudioRouterTo('/roadmaps/summary', O)).toBe(null)
  })
})
