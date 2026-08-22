/** Sticker board registry (`GET /api/sticker-board-registry`) — directory helpers. */

export type StickerBoardRegistryEntry = {
  id: string
  label?: string
  storage?: string
  owner_login?: string
  editors?: string[]
  viewers?: string[]
  preview_mtime?: string
}

export type StickerBoardRegistryPayload = {
  version?: number
  projects?: Record<string, StickerBoardRegistryEntry[]>
  validation_issues?: string[]
  /** When true, server filtered rows by session ACL — directory may be incomplete vs on-disk registry. */
  access_enforced?: boolean
  shared_login_configured?: boolean
  workspace_projects?: string[]
}

export type BoardDirectoryRow = {
  id: string
  label: string
  storage: string
  project: string
  ownerLogin: string | null
  editorsCount: number
  viewersCount: number
  previewMtime: string | null
}

/** Default “no activity” threshold (preview image mtime proxy). */
export const STALE_DAYS_THRESHOLD = 60

export function flattenRegistryToRows(
  data: StickerBoardRegistryPayload | null,
): BoardDirectoryRow[] {
  const out: BoardDirectoryRow[] = []
  for (const [proj, boards] of Object.entries(data?.projects ?? {})) {
    for (const b of boards ?? []) {
      const id = String(b.id ?? '').trim()
      if (!id) continue
      const label = String(b.label ?? 'Board').trim() || 'Board'
      const storage = b.storage === 'shared' ? 'shared' : 'local'
      const ol = b.owner_login != null ? String(b.owner_login).trim() : ''
      const editors = Array.isArray(b.editors) ? b.editors.filter((x) => typeof x === 'string') : []
      const viewers = Array.isArray(b.viewers) ? b.viewers.filter((x) => typeof x === 'string') : []
      const pm =
        b.preview_mtime != null && String(b.preview_mtime).trim()
          ? String(b.preview_mtime).trim()
          : null
      out.push({
        id,
        label,
        storage,
        project: proj,
        ownerLogin: ol || null,
        editorsCount: editors.length,
        viewersCount: viewers.length,
        previewMtime: pm,
      })
    }
  }
  return out
}

export function isUnowned(row: BoardDirectoryRow): boolean {
  return !row.ownerLogin
}

/**
 * Stale if no preview mtime or older than `staleDays` relative to `now`.
 * Preview mtime is a proxy for last visible activity, not sticker edits.
 */
export function isBoardStale(
  row: BoardDirectoryRow,
  now: Date,
  staleDays: number = STALE_DAYS_THRESHOLD,
): boolean {
  if (!row.previewMtime) return true
  const t = Date.parse(row.previewMtime)
  if (Number.isNaN(t)) return true
  const ageMs = now.getTime() - t
  return ageMs > staleDays * 24 * 60 * 60 * 1000
}

/** Recent preview capture (proxy for visible activity)—opposite of {@link isBoardStale}. */
export function isBoardFresh(
  row: BoardDirectoryRow,
  now: Date,
  staleDays: number = STALE_DAYS_THRESHOLD,
): boolean {
  return !isBoardStale(row, now, staleDays)
}

export function formatPreviewMtime(iso: string | null): string {
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

export type BoardSortKey =
  | 'label'
  | 'project'
  | 'storage'
  | 'owner'
  | 'previewMtime'
  | 'editorsCount'

export type SortDir = 'asc' | 'desc'

export function compareBoardRows(
  a: BoardDirectoryRow,
  b: BoardDirectoryRow,
  key: BoardSortKey,
  dir: SortDir,
): number {
  const m = dir === 'asc' ? 1 : -1
  switch (key) {
    case 'label':
      return m * a.label.localeCompare(b.label, undefined, { sensitivity: 'base' })
    case 'project':
      return m * a.project.localeCompare(b.project, undefined, { sensitivity: 'base' })
    case 'storage':
      return m * a.storage.localeCompare(b.storage)
    case 'owner':
      return m * (a.ownerLogin || '').localeCompare(b.ownerLogin || '')
    case 'previewMtime': {
      const ta = a.previewMtime ? Date.parse(a.previewMtime) : 0
      const tb = b.previewMtime ? Date.parse(b.previewMtime) : 0
      const na = Number.isNaN(ta) ? -Infinity : ta
      const nb = Number.isNaN(tb) ? -Infinity : tb
      return m * (na - nb)
    }
    case 'editorsCount':
      return m * (a.editorsCount - b.editorsCount)
    default:
      return 0
  }
}

export function sortBoardRows(
  rows: BoardDirectoryRow[],
  key: BoardSortKey,
  dir: SortDir,
): BoardDirectoryRow[] {
  return [...rows].sort((a, b) => compareBoardRows(a, b, key, dir))
}
