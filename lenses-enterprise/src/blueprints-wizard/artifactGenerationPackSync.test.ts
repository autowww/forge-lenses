import { describe, expect, it } from 'vitest'
import { artifactGenerationPreviewLines } from './artifactGenerationPackSync'
import type { WizardDomainJson } from './wizardDomainTypes'
import { ARTIFACT_SLICE_DISPLAY_LABELS, ARTIFACT_SLICE_KEYS } from './wizardDomainTypes'

describe('ARTIFACT_SLICE_DISPLAY_LABELS', () => {
  it('has a title for every artifact slice key', () => {
    for (const key of ARTIFACT_SLICE_KEYS) {
      expect(typeof ARTIFACT_SLICE_DISPLAY_LABELS[key]).toBe('string')
      expect(ARTIFACT_SLICE_DISPLAY_LABELS[key].length).toBeGreaterThan(0)
    }
  })
})

describe('artifactGenerationPreviewLines', () => {
  it('returns empty when no wizard domain', () => {
    expect(artifactGenerationPreviewLines(null)).toEqual([])
    expect(artifactGenerationPreviewLines(undefined)).toEqual([])
  })

  it('includes human titles for present artifacts', () => {
    const wd = {
      artifact_generation: {
        schema_version: 2,
        artifacts: {
          roadmap: {
            content: {},
            quality: {} as Record<string, { score: number; rationale: string }>,
            review_status: 'approved',
            locked: false,
            feedback: '',
            provenance: {
              generation_id: 'g1',
              created_at: '',
              provider: '',
              model: '',
              input_fingerprint: '',
              parent_generation_id: '',
              lineage: { upstream: [] },
            },
          },
          prd: {
            content: {},
            quality: {} as Record<string, { score: number; rationale: string }>,
            review_status: 'pending',
            locked: false,
            feedback: '',
            provenance: {
              generation_id: 'g2',
              created_at: '',
              provider: '',
              model: '',
              input_fingerprint: '',
              parent_generation_id: '',
              lineage: { upstream: [] },
            },
          },
        },
      },
    } as unknown as WizardDomainJson
    const lines = artifactGenerationPreviewLines(wd)
    expect(lines.some((l) => l.startsWith(`${ARTIFACT_SLICE_DISPLAY_LABELS.roadmap}:`))).toBe(true)
    expect(lines.some((l) => l.startsWith(`${ARTIFACT_SLICE_DISPLAY_LABELS.prd}:`))).toBe(true)
    expect(lines).toHaveLength(2)
  })
})
