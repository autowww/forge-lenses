import { describe, expect, it } from 'vitest'
import {
  SITE_INDEX_STALE_DAYS,
  hasCoverageGap,
  isIndexStale,
  siteAttentionBullets,
} from './sitePortfolio'
import type { WorkspaceState, WorkspaceWebsite } from '../api/workspace'

function site(partial: Partial<WorkspaceWebsite> & { name: string }): WorkspaceWebsite {
  const { name, ...rest } = partial
  return { name, ...rest }
}

describe('hasCoverageGap', () => {
  it('is false when totals align', () => {
    expect(hasCoverageGap(site({ name: 'a', html_total: 10, html_indexed: 10 }))).toBe(false)
  })
  it('is true when indexed below total', () => {
    expect(hasCoverageGap(site({ name: 'a', html_total: 10, html_indexed: 3 }))).toBe(true)
  })
  it('is false when no html', () => {
    expect(hasCoverageGap(site({ name: 'a', html_total: 0, html_indexed: 0 }))).toBe(false)
  })
})

describe('isIndexStale', () => {
  const now = new Date('2025-06-15T12:00:00Z')

  it('treats missing mtime as stale', () => {
    expect(isIndexStale(site({ name: 'a' }), now, SITE_INDEX_STALE_DAYS)).toBe(true)
  })

  it('treats old mtime as stale', () => {
    const old = new Date('2024-01-01T00:00:00Z').getTime() / 1000
    expect(isIndexStale(site({ name: 'a', index_html_mtime: old }), now, 90)).toBe(true)
  })

  it('treats recent mtime as fresh', () => {
    const recent = new Date('2025-06-01T00:00:00Z').getTime() / 1000
    expect(isIndexStale(site({ name: 'a', index_html_mtime: recent }), now, 90)).toBe(false)
  })
})

describe('siteAttentionBullets', () => {
  it('returns a win-style bullet when nothing flagged', () => {
    const state: WorkspaceState = {
      workspace_root: '/x',
      children: [],
      roadmaps: [],
      websites: [
        {
          name: 's',
          html_total: 1,
          html_indexed: 1,
          index_html_mtime: Date.now() / 1000,
        } as WorkspaceWebsite,
      ],
    }
    const b = siteAttentionBullets(state, new Date())
    expect(b.length).toBeGreaterThan(0)
    expect(b[0]).toMatch(/No blocking/)
  })
})
