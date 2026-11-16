import { useCallback, useEffect, useRef, useState } from 'react'
import { apiGetJson } from '../api/http'
import { useWorkspace } from '../context/WorkspaceContext'
import { classifyFetchError } from '../lib/classifyFetchError'
import type { StickerBoardRegistryPayload } from '../lib/boardDirectory'
import { readBoardRegistryCache, writeBoardRegistryCache } from '../lib/boardRegistryCache'

export type BoardRegistryFetchSnapshot = {
  displayPayload: StickerBoardRegistryPayload | null
  displaySnapshotAt: string | null
  lastLiveSuccessAt: string | null
  servingFromCacheAfterFailure: boolean
  isFetching: boolean
  isHydrating: boolean
  lastError: string | null
  refresh: () => Promise<void>
  /** When the workspace scan is not ready, registry fetch is deferred. */
  workspaceReady: boolean
}

/** Collapsed “technical details” for registry fetch failures (not shown inline). */
function errorMessage(e: unknown): string {
  const c = classifyFetchError(e)
  const parts = [c.detail, c.httpStatus != null ? `Response status: ${c.httpStatus}` : null].filter(
    (x): x is string => Boolean(x && String(x).trim()),
  )
  return parts.join('\n') || c.summary
}

/**
 * Loads `/api/sticker-board-registry` after `workspace_root` is known, with per-workspace localStorage fallback.
 */
export function useBoardRegistry(): BoardRegistryFetchSnapshot {
  const { state, loading: workspaceLoading, error: workspaceError } = useWorkspace()
  const wsRoot = state?.workspace_root?.trim() || null
  const workspaceReady = !workspaceLoading && Boolean(wsRoot) && !workspaceError

  const [displayPayload, setDisplayPayload] = useState<StickerBoardRegistryPayload | null>(null)
  const [displaySnapshotAt, setDisplaySnapshotAt] = useState<string | null>(null)
  const [lastLiveSuccessAt, setLastLiveSuccessAt] = useState<string | null>(null)
  const [servingFromCacheAfterFailure, setServingFromCacheAfterFailure] = useState(false)
  const [isFetching, setIsFetching] = useState(false)
  const [isHydrating, setIsHydrating] = useState(true)
  const [lastError, setLastError] = useState<string | null>(null)

  const displayPayloadRef = useRef(displayPayload)
  displayPayloadRef.current = displayPayload

  const fetchRegistry = useCallback(async (root: string) => {
    setIsFetching(true)
    setLastError(null)
    try {
      const d = await apiGetJson<StickerBoardRegistryPayload>('/api/sticker-board-registry')
      const iso = new Date().toISOString()
      setDisplayPayload(d)
      setDisplaySnapshotAt(iso)
      setLastLiveSuccessAt(iso)
      setServingFromCacheAfterFailure(false)
      writeBoardRegistryCache(root, d, iso)
    } catch (e) {
      const msg = errorMessage(e)
      setLastError(msg)
      const cur = displayPayloadRef.current
      if (cur) {
        setServingFromCacheAfterFailure(true)
      } else {
        const disk = readBoardRegistryCache(root)
        if (disk) {
          setDisplayPayload(disk.payload)
          setDisplaySnapshotAt(disk.savedAtIso)
          setServingFromCacheAfterFailure(true)
        }
      }
    } finally {
      setIsFetching(false)
      setIsHydrating(false)
    }
  }, [])

  useEffect(() => {
    if (workspaceLoading) return
    if (!wsRoot) {
      setIsHydrating(false)
      setDisplayPayload(null)
      setDisplaySnapshotAt(null)
      setLastError(workspaceError ? 'Workspace scan failed — board registry unavailable until the workspace loads.' : null)
      return
    }

    setIsHydrating(true)
    const disk = readBoardRegistryCache(wsRoot)
    if (disk) {
      setDisplayPayload(disk.payload)
      setDisplaySnapshotAt(disk.savedAtIso)
      displayPayloadRef.current = disk.payload
    } else {
      setDisplayPayload(null)
      setDisplaySnapshotAt(null)
      displayPayloadRef.current = null
    }
    setServingFromCacheAfterFailure(false)
    setLastError(null)
    void fetchRegistry(wsRoot)
  }, [workspaceLoading, wsRoot, workspaceError, fetchRegistry])

  const refresh = useCallback(async () => {
    if (!wsRoot) return
    setIsHydrating(false)
    await fetchRegistry(wsRoot)
  }, [fetchRegistry, wsRoot])

  return {
    displayPayload,
    displaySnapshotAt,
    lastLiveSuccessAt,
    servingFromCacheAfterFailure,
    isFetching,
    isHydrating: isHydrating || workspaceLoading,
    lastError,
    refresh,
    workspaceReady,
  }
}
