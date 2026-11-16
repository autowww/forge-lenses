import { describe, expect, it } from 'vitest'
import {
  branchNamingRows,
  categoryMixFromBranches,
  formatBranchingModel,
  formatMergeGuardrails,
  formatTeamProfileSentence,
  laneVolumesForChart,
  matchPolicyResolutionStepIndex,
  recommendationRows,
} from './branchingViewModel'

describe('formatBranchingModel', () => {
  it('labels team_tier', () => {
    expect(formatBranchingModel('team_tier').code).toBe('team_tier')
    expect(formatBranchingModel('team_tier').title).toContain('Team tier')
  })

  it('labels forge_lanes', () => {
    expect(formatBranchingModel('forge_lanes').title).toContain('Forge lanes')
  })
})

describe('formatMergeGuardrails', () => {
  it('summarizes team-style gates', () => {
    const v = formatMergeGuardrails({
      require_pr: true,
      required_approvals: 1,
      require_green_checks: true,
    })
    expect(v.summary).toContain('governed')
    expect(v.bullets.some((b) => b.includes('pull request'))).toBe(true)
    expect(v.bullets.some((b) => b.includes('approval'))).toBe(true)
    expect(v.bullets.some((b) => b.includes('automated'))).toBe(true)
  })
})

describe('recommendationRows', () => {
  it('sorts keys and maps known titles', () => {
    const rows = recommendationRows({
      hotfix: 'fix/foo',
      charge_work: 'feature/bar',
    })
    expect(rows[0].key).toBe('charge_work')
    expect(rows[0].title).toBe('Charge and change work')
    expect(rows[1].title).toBe('Hotfixes')
  })
})

describe('branchNamingRows', () => {
  it('includes configured prefixes', () => {
    const rows = branchNamingRows({
      feature_prefix: 'feature/',
      fix_prefix: 'fix/',
      product_prefix: 'product/',
    })
    expect(rows.find((r) => r.lane === 'Feature')?.prefix).toBe('feature/')
    expect(rows.find((r) => r.lane === 'Fix')?.prefix).toBe('fix/')
  })
})

describe('laneVolumesForChart', () => {
  it('orders lanes and reads counts', () => {
    const rows = laneVolumesForChart({
      feature: [{ name: 'feature/a' }],
      main: [],
      fix: [{ name: 'fix/b' }, { name: 'fix/c' }],
    })
    const ix = (lane: string) => rows.findIndex((r) => r.lane === lane)
    expect(ix('main')).toBeLessThan(ix('feature'))
    expect(rows.find((r) => r.lane === 'fix')?.count).toBe(2)
    expect(rows.find((r) => r.lane === 'main')?.count).toBe(0)
  })
})

describe('categoryMixFromBranches', () => {
  it('aggregates categories', () => {
    const mix = categoryMixFromBranches([
      { category: 'feature' },
      { category: 'feature' },
      { category: 'main' },
    ])
    expect(mix.find((m) => m.category === 'feature')?.count).toBe(2)
    expect(mix.find((m) => m.category === 'main')?.count).toBe(1)
  })
})

describe('matchPolicyResolutionStepIndex', () => {
  it('matches forge config', () => {
    expect(matchPolicyResolutionStepIndex('forge/forge.config.yaml')).toBe(2)
  })
  it('matches branching yml', () => {
    expect(matchPolicyResolutionStepIndex('forge/branching.yml')).toBe(0)
  })
})

describe('formatTeamProfileSentence', () => {
  it('joins glosses', () => {
    const s = formatTeamProfileSentence({
      team_scale: 'team',
      topology: 'single',
      cicd_maturity: 'standard',
    })
    expect(s).toContain('Team tier')
    expect(s).toContain('Single repo')
  })
})
