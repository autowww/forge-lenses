import { describe, expect, it } from 'vitest'

import { resolveLensesJsonApiOrigin } from './http'

describe('resolveLensesJsonApiOrigin', () => {
  it('uses page origin when VITE base is empty', () => {
    expect(resolveLensesJsonApiOrigin(undefined, 'http://localhost:5173')).toBe('http://localhost:5173')
    expect(resolveLensesJsonApiOrigin('  ', 'http://127.0.0.1:9000')).toBe('http://127.0.0.1:9000')
  })

  it('parses explicit base with scheme', () => {
    expect(resolveLensesJsonApiOrigin('http://127.0.0.1:8080/', 'http://localhost:5173')).toBe(
      'http://127.0.0.1:8080',
    )
  })

  it('adds http when scheme omitted', () => {
    expect(resolveLensesJsonApiOrigin('127.0.0.1:9999', 'http://localhost:5173')).toBe('http://127.0.0.1:9999')
  })

  it('falls back to page origin on invalid base', () => {
    expect(resolveLensesJsonApiOrigin(':::not-a-url', 'http://localhost:5173')).toBe('http://localhost:5173')
  })
})
