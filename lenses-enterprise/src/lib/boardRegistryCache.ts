import type { StickerBoardRegistryPayload } from './boardDirectory'

const KEY_PREFIX = 'forge-studio.sticker-board-registry.v1'

function workspaceCacheTag(workspaceRoot: string | null | undefined): string {
  const root = (workspaceRoot ?? '').trim()
  if (!root) return 'pending'
  let h = 0
  for (let i = 0; i < root.length; i++) h = (Math.imul(31, h) + root.charCodeAt(i)) | 0
  return `w${(h >>> 0).toString(16)}`
}

export function boardRegistryStorageKey(workspaceRoot: string | null | undefined): string {
  return `${KEY_PREFIX}:${workspaceCacheTag(workspaceRoot)}`
}

export type BoardRegistryCacheRecord = {
  savedAtIso: string
  payload: StickerBoardRegistryPayload
}

function safeParse(raw: string | null): BoardRegistryCacheRecord | null {
  if (!raw) return null
  try {
    const o = JSON.parse(raw) as { savedAtIso?: string; payload?: StickerBoardRegistryPayload }
    if (!o || typeof o.savedAtIso !== 'string' || !o.payload || typeof o.payload !== 'object') return null
    return { savedAtIso: o.savedAtIso, payload: o.payload }
  } catch {
    return null
  }
}

export function readBoardRegistryCache(workspaceRoot: string | null | undefined): BoardRegistryCacheRecord | null {
  if (typeof window === 'undefined' || !window.localStorage) return null
  return safeParse(window.localStorage.getItem(boardRegistryStorageKey(workspaceRoot)))
}

export function writeBoardRegistryCache(
  workspaceRoot: string | null | undefined,
  payload: StickerBoardRegistryPayload,
  savedAtIso: string,
): void {
  if (typeof window === 'undefined' || !window.localStorage) return
  try {
    window.localStorage.setItem(
      boardRegistryStorageKey(workspaceRoot),
      JSON.stringify({ savedAtIso, payload }),
    )
  } catch {
    /* quota or private mode */
  }
}

export function clearBoardRegistryCache(workspaceRoot: string | null | undefined): void {
  if (typeof window === 'undefined' || !window.localStorage) return
  try {
    window.localStorage.removeItem(boardRegistryStorageKey(workspaceRoot))
  } catch {
    /* ignore */
  }
}
