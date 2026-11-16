import { useCallback, useEffect, useState } from 'react'
import { apiGetJson } from '../api/http'
import { classifyFetchError, type ClassifiedFetchFailure, type FetchFailureKind } from '../lib/classifyFetchError'
import {
  formatSnapshotAge,
  formatSnapshotTimestamp,
  readJsonSnapshot,
  writeJsonSnapshot,
} from '../lib/studioJsonSnapshot'

export type ResilientJsonPhase = 'loading' | 'ok' | 'empty' | 'stale' | 'error'

export type ResilientJsonBlockResult<T> = {
  phase: ResilientJsonPhase
  data: T | null
  /** True when `data` comes from session snapshot after a failed refresh. */
  fromSnapshot: boolean
  snapshotFetchedAt: number | null
  snapshotAgeLabel: string | null
  snapshotTimeLabel: string | null
  failure: ClassifiedFetchFailure | null
  /** Distinct from HTTP empty — scan not run, repo missing, etc. */
  failureKind: FetchFailureKind | null
  retry: () => void
}

const DEFAULT_STALE_MAX_MS = 1000 * 60 * 60 * 24 * 7 // 7d

function isEmptyPayload<T>(data: T | null): boolean {
  if (data == null) return true
  if (typeof data === 'object' && !Array.isArray(data) && Object.keys(data as object).length === 0) return true
  return false
}

/**
 * Fetch JSON for one dashboard block with snapshot fallback and block-level retry.
 */
export function useResilientJsonBlock<T>(
  apiPath: string | null,
  options?: {
    /** Max age of snapshot to still treat as displayable partial value. */
    staleMaxMs?: number
    /** Storage key; default is apiPath. */
    snapshotKey?: string
    /** When true, successful empty object/array counts as `empty` not `ok`. */
    treatEmptyAsEmpty?: boolean
    /** When this value changes (e.g. workspace `resolved_at`), refetch the block. */
    refreshKey?: string | number | null
  },
): ResilientJsonBlockResult<T> {
  const staleMaxMs = options?.staleMaxMs ?? DEFAULT_STALE_MAX_MS
  const snapshotKey = options?.snapshotKey ?? apiPath ?? ''
  const treatEmpty = options?.treatEmptyAsEmpty ?? false
  const refreshKey = options?.refreshKey ?? null
  const [generation, setGeneration] = useState(0)
  const [phase, setPhase] = useState<ResilientJsonPhase>(() => (apiPath ? 'loading' : 'error'))
  const [data, setData] = useState<T | null>(null)
  const [fromSnapshot, setFromSnapshot] = useState(false)
  const [snapshotFetchedAt, setSnapshotFetchedAt] = useState<number | null>(null)
  const [failure, setFailure] = useState<ClassifiedFetchFailure | null>(null)

  const retry = useCallback(() => setGeneration((g) => g + 1), [])

  useEffect(() => {
    if (!apiPath) {
      setPhase('error')
      setData(null)
      setFromSnapshot(false)
      setSnapshotFetchedAt(null)
      setFailure({
        kind: 'unknown',
        summary: 'No API path configured.',
      })
      return
    }

    let cancelled = false
    setPhase('loading')
    setFailure(null)

    void (async () => {
      try {
        const fresh = await apiGetJson<T>(apiPath)
        if (cancelled) return
        writeJsonSnapshot(snapshotKey, fresh)
        if (treatEmpty && isEmptyPayload(fresh)) {
          setData(fresh)
          setFromSnapshot(false)
          setSnapshotFetchedAt(null)
          setPhase('empty')
          return
        }
        setData(fresh)
        setFromSnapshot(false)
        setSnapshotFetchedAt(null)
        setPhase('ok')
      } catch (err) {
        if (cancelled) return
        const classified = classifyFetchError(err)
        setFailure(classified)
        const snap = readJsonSnapshot<T>(snapshotKey)
        const ageOk = snap && Date.now() - snap.fetchedAt <= staleMaxMs
        if (snap && ageOk) {
          setData(snap.data)
          setFromSnapshot(true)
          setSnapshotFetchedAt(snap.fetchedAt)
          setPhase('stale')
        } else if (snap && !ageOk) {
          setData(null)
          setFromSnapshot(false)
          setSnapshotFetchedAt(null)
          setPhase('error')
        } else {
          setData(null)
          setFromSnapshot(false)
          setSnapshotFetchedAt(null)
          setPhase('error')
        }
      }
    })()

    return () => {
      cancelled = true
    }
  }, [apiPath, snapshotKey, staleMaxMs, treatEmpty, generation, refreshKey])

  const now = Date.now()
  const snapshotAgeLabel = snapshotFetchedAt != null ? formatSnapshotAge(snapshotFetchedAt, now) : null
  const snapshotTimeLabel = snapshotFetchedAt != null ? formatSnapshotTimestamp(snapshotFetchedAt) : null

  return {
    phase,
    data,
    fromSnapshot,
    snapshotFetchedAt,
    snapshotAgeLabel,
    snapshotTimeLabel,
    failure,
    failureKind: failure?.kind ?? null,
    retry,
  }
}
