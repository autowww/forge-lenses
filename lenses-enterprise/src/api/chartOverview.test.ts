import { describe, expect, it } from 'vitest'
import {
  linesAddedByRepo,
  perRepoLinesByKey,
  workspaceLocTotal,
  type OverviewChartPayload,
} from './chartOverview'

describe('linesAddedByRepo', () => {
  it('uses lowercase keys for lookup', () => {
    const payload: OverviewChartPayload = {
      charts: {
        loc_added_horizontal: {
          rows: [{ name: 'MyRepo', value: 42 }],
        },
      },
    }
    const m = linesAddedByRepo(payload)
    expect(m.get('myrepo')).toBe(42)
    expect(m.has('MyRepo')).toBe(false)
  })
})

describe('workspaceLocTotal', () => {
  it('sums loc_share_donut rows', () => {
    const payload: OverviewChartPayload = {
      charts: {
        loc_share_donut: {
          rows: [
            { name: 'a', value: 100 },
            { name: 'b', value: 50 },
          ],
        },
      },
    }
    expect(workspaceLocTotal(payload)).toBe(150)
  })

  it('falls back to loc_total_bars', () => {
    const payload: OverviewChartPayload = {
      charts: {
        loc_total_bars: {
          rows: [{ name: 'x', value: 10 }],
        },
      },
    }
    expect(workspaceLocTotal(payload)).toBe(10)
  })
})

describe('perRepoLinesByKey', () => {
  it('normalizes keys for tier lookup', () => {
    const payload: OverviewChartPayload = {
      kpi_trends: {
        lines_added: {
          per_repo_lines: {
            'Some Name': { tier: 'green', median_prior_6: 5, period_totals: [1, 2, 3, 4, 5, 6, 7] },
          },
        },
      },
    }
    const m = perRepoLinesByKey(payload)
    expect(m.get('some name')?.tier).toBe('green')
  })
})
