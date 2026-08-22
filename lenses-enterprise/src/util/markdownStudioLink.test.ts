import { describe, expect, it } from 'vitest'
import { markdownHrefToStudioTo, stripStudioUrlPath } from './markdownStudioLink'

const ORIGIN = 'http://127.0.0.1:8080'

describe('stripStudioUrlPath', () => {
  it('strips /studio prefix', () => {
    expect(stripStudioUrlPath('/studio/plan')).toBe('/plan')
    expect(stripStudioUrlPath('/studio')).toBe('/')
  })
})

describe('markdownHrefToStudioTo', () => {
  it('maps root-relative plan and docs paths', () => {
    expect(markdownHrefToStudioTo('/plan?tab=story&id=1', ORIGIN)).toBe('/plan?tab=story&id=1')
    expect(markdownHrefToStudioTo('/docs/foo.html', ORIGIN)).toBe('/view/docs/foo.html')
    expect(markdownHrefToStudioTo('/local-site/x/y.html', ORIGIN)).toBe('/view/local-site/x/y.html')
  })

  it('returns null for api and fragments', () => {
    expect(markdownHrefToStudioTo('/api/foo', ORIGIN)).toBe(null)
    expect(markdownHrefToStudioTo('#x', ORIGIN)).toBe(null)
  })

  it('maps same-origin absolute URLs', () => {
    expect(markdownHrefToStudioTo(`${ORIGIN}/plan?tab=story`, ORIGIN)).toBe('/plan?tab=story')
    expect(markdownHrefToStudioTo(`${ORIGIN}/studio/plan?x=1`, ORIGIN)).toBe('/plan?x=1')
  })

  it('returns null for other origins', () => {
    expect(markdownHrefToStudioTo('https://example.com/x', ORIGIN)).toBe(null)
  })
})
