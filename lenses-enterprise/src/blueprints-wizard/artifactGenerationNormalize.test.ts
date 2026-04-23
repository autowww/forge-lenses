import { describe, expect, it } from 'vitest'
import { normalizeArtifactGeneration, normalizeQualityRubric } from './wizardDomainNormalize'
import { QUALITY_DIMENSIONS } from './wizardDomainTypes'

describe('normalizeQualityRubric', () => {
  it('fills all six dimensions', () => {
    const q = normalizeQualityRubric({ groundedness: { score: 2, rationale: 'x' } })
    for (const dim of QUALITY_DIMENSIONS) {
      expect(q[dim]).toBeDefined()
      expect(q[dim].score).toBeGreaterThanOrEqual(0)
      expect(q[dim].score).toBeLessThanOrEqual(1)
    }
    expect(q.groundedness.score).toBe(1)
  })
})

describe('normalizeArtifactGeneration', () => {
  it('defaults empty artifacts', () => {
    const ag = normalizeArtifactGeneration({})
    expect(ag.schema_version).toBeGreaterThanOrEqual(1)
    expect(Object.keys(ag.artifacts)).toHaveLength(0)
  })
})
