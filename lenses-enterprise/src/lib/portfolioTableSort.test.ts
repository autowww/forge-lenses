import { describe, expect, it } from 'vitest'
import type { RepoPortfolioRow } from './workspacePortfolio'
import { comparePortfolioRows, partitionByHealth, sortPortfolioRows } from './portfolioTableSort'

function row(partial: Partial<RepoPortfolioRow> & { name: string }): RepoPortfolioRow {
  return {
    health: 'healthy',
    riskScore: 0,
    standardsScore: null,
    standardsTier: null,
    dirty: false,
    roadmapCount: 0,
    wbsCount: 0,
    linesAdded7d: null,
    linesPrev7d: null,
    linesTier: null,
    linesMedianPrior6: null,
    evidenceFlags: 0,
    forgeHint: null,
    ...partial,
  }
}

describe('sortPortfolioRows', () => {
  it('sorts by risk descending', () => {
    const a = row({ name: 'a', riskScore: 1 })
    const b = row({ name: 'b', riskScore: 5 })
    const out = sortPortfolioRows([a, b], 'riskScore', 'desc')
    expect(out[0].name).toBe('b')
  })

  it('sorts by name ascending', () => {
    const a = row({ name: 'zebra' })
    const b = row({ name: 'alpha' })
    const out = sortPortfolioRows([a, b], 'name', 'asc')
    expect(out[0].name).toBe('alpha')
  })
})

describe('comparePortfolioRows', () => {
  it('orders health at_risk before healthy', () => {
    const a = row({ name: 'x', health: 'at_risk' })
    const b = row({ name: 'y', health: 'healthy' })
    expect(comparePortfolioRows(a, b, 'health', 'asc')).toBeLessThan(0)
  })
})

describe('partitionByHealth', () => {
  it('splits tiers', () => {
    const p = partitionByHealth([
      row({ name: 'r', health: 'at_risk' }),
      row({ name: 'w', health: 'watch' }),
      row({ name: 'h', health: 'healthy' }),
    ])
    expect(p.at_risk).toHaveLength(1)
    expect(p.watch).toHaveLength(1)
    expect(p.healthy).toHaveLength(1)
  })
})
