/**
 * Browser-local last-known-good JSON for degraded UX (sessionStorage).
 * Not a security boundary — convenience only.
 */

const PREFIX = 'studio.snapshot.v1.'

export type JsonSnapshotEnvelope<T = unknown> = {
  /** Epoch ms when the snapshot was written after a successful fetch. */
  fetchedAt: number
  source: 'network'
  data: T
}

export function snapshotStorageKey(logicalKey: string): string {
  return `${PREFIX}${logicalKey.replace(/\s+/g, '')}`
}

export function readJsonSnapshot<T>(logicalKey: string): JsonSnapshotEnvelope<T> | null {
  try {
    const raw = sessionStorage.getItem(snapshotStorageKey(logicalKey))
    if (!raw) return null
    const parsed = JSON.parse(raw) as JsonSnapshotEnvelope<T>
    if (!parsed || typeof parsed.fetchedAt !== 'number' || !('data' in parsed)) return null
    return parsed
  } catch {
    return null
  }
}

export function writeJsonSnapshot<T>(logicalKey: string, data: T): void {
  try {
    const env: JsonSnapshotEnvelope<T> = { fetchedAt: Date.now(), source: 'network', data }
    sessionStorage.setItem(snapshotStorageKey(logicalKey), JSON.stringify(env))
  } catch {
    /* quota / private mode */
  }
}

export function formatSnapshotAge(fetchedAt: number, now: number = Date.now()): string {
  const sec = Math.max(0, Math.floor((now - fetchedAt) / 1000))
  if (sec < 60) return 'just now'
  const min = Math.floor(sec / 60)
  if (min < 60) return `${min} min ago`
  const hr = Math.floor(min / 60)
  if (hr < 48) return `${hr} h ago`
  const days = Math.floor(hr / 24)
  return `${days} d ago`
}

export function formatSnapshotTimestamp(fetchedAt: number): string {
  try {
    return new Date(fetchedAt).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
  } catch {
    return 'unknown time'
  }
}
