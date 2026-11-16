import { describe, expect, it } from 'vitest'
import { friendlyDocumentTitle, friendlyRepoLabel } from './planDisplayNames'

describe('planDisplayNames', () => {
  it('friendlyDocumentTitle uses file stem with spaces', () => {
    expect(friendlyDocumentTitle('Situ8/docs/requirements/WBS.md')).toBe('WBS')
    expect(friendlyDocumentTitle('foo/ROADMAP.md')).toBe('ROADMAP')
  })

  it('friendlyRepoLabel uses last path segment', () => {
    expect(friendlyRepoLabel('Situ8')).toBe('Situ8')
    expect(friendlyRepoLabel('org/my-product')).toBe('my-product')
  })
})
