/**
 * Client-side mirror of `lenses.blueprints_wizard.artifact_generation_dependencies.resolve_requested_artifact_keys`
 * for validation, tests, and UI hints. Server remains authoritative.
 */

import {
  ARTIFACT_SLICE_KEYS,
  ENGINEERING_ARTIFACT_SLICE_KEYS,
  EXECUTION_ARTIFACT_SLICE_KEYS,
  PLANNING_ARTIFACT_SLICE_KEYS,
  PLANNING_ENGINEERING_ARTIFACT_SLICE_KEYS,
  type ArtifactSliceKey,
} from './wizardDomainTypes'

const ALL = new Set<string>(ARTIFACT_SLICE_KEYS)
const PLANNING = new Set<string>(PLANNING_ARTIFACT_SLICE_KEYS)
const ENGINEERING = new Set<string>(ENGINEERING_ARTIFACT_SLICE_KEYS)
const EXECUTION = new Set<string>(EXECUTION_ARTIFACT_SLICE_KEYS)
const PLANNING_ENGINEERING = new Set<string>(PLANNING_ENGINEERING_ARTIFACT_SLICE_KEYS)

function sortedKeys(keys: Set<string>): readonly ArtifactSliceKey[] {
  return [...keys].sort() as ArtifactSliceKey[]
}

export type ResolveRequestedArtifactKeysResult =
  | { ok: true; keys: readonly ArtifactSliceKey[] }
  | { ok: false; error: 'invalid_artifact_keys' }
  | { ok: false; error: 'invalid_artifact_key'; detail: string }

export type ArtifactGenerationBundleAlias =
  | import('./wizardDomainTypes').ArtifactGenerationBundle
  | 'full'
  | ''

/**
 * Resolve which artifact slices a generate-artifacts request targets (parity with Python).
 * Body: optional `artifact_keys` (non-empty list), else optional `artifact` (single key),
 * else optional `artifact_bundle` (`planning` | `engineering` | `all` | `full` | `execution` | `complete` | `full_stack`), else default planning bundle.
 */
export function resolveRequestedArtifactKeys(body: Record<string, unknown>): ResolveRequestedArtifactKeysResult {
  const rawList = body.artifact_keys
  if (Array.isArray(rawList) && rawList.length > 0) {
    const keys = new Set<string>()
    for (const x of rawList) {
      const k = String(x).trim()
      if (k && ALL.has(k)) keys.add(k)
    }
    if (keys.size === 0) return { ok: false, error: 'invalid_artifact_keys' }
    return { ok: true, keys: sortedKeys(keys) }
  }

  const artRaw = body.artifact
  if (artRaw != null && String(artRaw).trim() !== '') {
    const key = String(artRaw).trim()
    if (!ALL.has(key)) return { ok: false, error: 'invalid_artifact_key', detail: key }
    return { ok: true, keys: [key as ArtifactSliceKey] }
  }

  const bundle = String(body.artifact_bundle ?? '')
    .trim()
    .toLowerCase() as ArtifactGenerationBundleAlias
  if (bundle === 'engineering') return { ok: true, keys: sortedKeys(ENGINEERING) }
  if (bundle === 'planning') return { ok: true, keys: sortedKeys(PLANNING) }
  if (bundle === 'execution') return { ok: true, keys: sortedKeys(EXECUTION) }
  if (bundle === 'all' || bundle === 'full') return { ok: true, keys: sortedKeys(PLANNING_ENGINEERING) }
  if (bundle === 'complete' || bundle === 'full_stack') return { ok: true, keys: sortedKeys(ALL) }

  return { ok: true, keys: sortedKeys(PLANNING) }
}
