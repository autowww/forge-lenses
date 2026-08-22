import { describe, expect, it } from 'vitest'
import { resolveRequestedArtifactKeys } from './resolveRequestedArtifactKeys'
import {
  ARTIFACT_SLICE_KEYS,
  ENGINEERING_ARTIFACT_SLICE_KEYS,
  EXECUTION_ARTIFACT_SLICE_KEYS,
  PLANNING_ARTIFACT_SLICE_KEYS,
  PLANNING_ENGINEERING_ARTIFACT_SLICE_KEYS,
} from './wizardDomainTypes'

function sorted<T extends string>(arr: readonly T[]): string[] {
  return [...arr].map(String).sort()
}

describe('resolveRequestedArtifactKeys', () => {
  it('defaults to planning bundle (parity with Python empty body)', () => {
    const r = resolveRequestedArtifactKeys({})
    expect(r.ok).toBe(true)
    if (!r.ok) return
    expect(sorted(r.keys)).toEqual(sorted(PLANNING_ARTIFACT_SLICE_KEYS))
  })

  it('respects artifact_bundle engineering', () => {
    const r = resolveRequestedArtifactKeys({ artifact_bundle: 'engineering' })
    expect(r.ok).toBe(true)
    if (!r.ok) return
    expect(sorted(r.keys)).toEqual(sorted(ENGINEERING_ARTIFACT_SLICE_KEYS))
  })

  it('respects artifact_bundle planning', () => {
    const r = resolveRequestedArtifactKeys({ artifact_bundle: 'planning' })
    expect(r.ok).toBe(true)
    if (!r.ok) return
    expect(sorted(r.keys)).toEqual(sorted(PLANNING_ARTIFACT_SLICE_KEYS))
  })

  it('maps all and full to planning plus engineering (not execution)', () => {
    for (const b of ['all', 'full'] as const) {
      const r = resolveRequestedArtifactKeys({ artifact_bundle: b })
      expect(r.ok).toBe(true)
      if (!r.ok) return
      expect(sorted(r.keys)).toEqual(sorted(PLANNING_ENGINEERING_ARTIFACT_SLICE_KEYS))
    }
  })

  it('maps execution bundle to execution slices', () => {
    const r = resolveRequestedArtifactKeys({ artifact_bundle: 'execution' })
    expect(r.ok).toBe(true)
    if (!r.ok) return
    expect(sorted(r.keys)).toEqual(sorted(EXECUTION_ARTIFACT_SLICE_KEYS))
  })

  it('maps complete and full_stack to every slice key', () => {
    for (const b of ['complete', 'full_stack'] as const) {
      const r = resolveRequestedArtifactKeys({ artifact_bundle: b })
      expect(r.ok).toBe(true)
      if (!r.ok) return
      expect(sorted(r.keys)).toEqual(sorted(ARTIFACT_SLICE_KEYS))
    }
  })

  it('parses artifact_keys list', () => {
    const r = resolveRequestedArtifactKeys({
      artifact_keys: ['roadmap', 'prd', 'nonsense'],
    })
    expect(r.ok).toBe(true)
    if (!r.ok) return
    expect(new Set(r.keys)).toEqual(new Set(['prd', 'roadmap']))
  })

  it('returns invalid_artifact_keys when list has no valid keys', () => {
    const r = resolveRequestedArtifactKeys({ artifact_keys: ['', 'bad'] })
    expect(r.ok).toBe(false)
    if (r.ok) return
    expect(r.error).toBe('invalid_artifact_keys')
  })

  it('parses single artifact', () => {
    const r = resolveRequestedArtifactKeys({ artifact: 'roadmap' })
    expect(r.ok).toBe(true)
    if (!r.ok) return
    expect(r.keys).toEqual(['roadmap'])
  })

  it('returns invalid_artifact_key for unknown single artifact', () => {
    const r = resolveRequestedArtifactKeys({ artifact: 'not_a_key' })
    expect(r.ok).toBe(false)
    if (r.ok) return
    expect(r.error).toBe('invalid_artifact_key')
    if (r.error === 'invalid_artifact_key') {
      expect(r.detail).toBe('not_a_key')
    }
  })

  it('artifact_keys wins over artifact when both present', () => {
    const r = resolveRequestedArtifactKeys({
      artifact_keys: ['prd'],
      artifact: 'roadmap',
    })
    expect(r.ok).toBe(true)
    if (!r.ok) return
    expect(r.keys).toEqual(['prd'])
  })
})
