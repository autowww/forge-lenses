import type { StickerBoardRegistryPayload } from './boardDirectory'
import { flattenRegistryToRows } from './boardDirectory'

export type BoardRegistryDataKind = 'none' | 'empty' | 'partial' | 'loaded'

/**
 * Surface classification for hub UX (not API errors).
 * - **empty** — successful payload, zero boards in view.
 * - **partial** — registry or policy signals incompleteness (validation issues or ACL-filtered snapshot).
 * - **loaded** — rows present and no partial signals.
 */
export function classifyBoardRegistryData(data: StickerBoardRegistryPayload | null): BoardRegistryDataKind {
  if (!data) return 'none'
  const rows = flattenRegistryToRows(data)
  const partialSignals =
    (data.validation_issues?.length ?? 0) > 0 || data.access_enforced === true
  if (partialSignals) return 'partial'
  if (rows.length === 0) return 'empty'
  return 'loaded'
}

export function formatRegistrySnapshotLabel(iso: string | null | undefined): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short',
    })
  } catch {
    return iso
  }
}
