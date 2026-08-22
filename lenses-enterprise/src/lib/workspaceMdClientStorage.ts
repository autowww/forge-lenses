const RECENT_KEY = 'lenses-studio.workspace-md.recent'
const PINNED_KEY = 'lenses-studio.workspace-md.pinned'
const MAX_RECENT = 14
const MAX_PINNED = 28

function readStringArray(key: string): string[] {
  try {
    const raw = localStorage.getItem(key)
    if (!raw) return []
    const v = JSON.parse(raw) as unknown
    if (!Array.isArray(v)) return []
    return v.filter((x): x is string => typeof x === 'string' && x.trim().length > 0).map((s) => s.trim())
  } catch {
    return []
  }
}

function writeStringArray(key: string, items: string[]) {
  try {
    localStorage.setItem(key, JSON.stringify(items))
  } catch {
    /* quota or private mode */
  }
}

export function readWorkspaceMdRecent(): string[] {
  return readStringArray(RECENT_KEY)
}

export function recordWorkspaceMdRecent(relPath: string) {
  const p = relPath.trim()
  if (!p) return
  const prev = readWorkspaceMdRecent().filter((x) => x !== p)
  prev.unshift(p)
  writeStringArray(RECENT_KEY, prev.slice(0, MAX_RECENT))
}

export function clearWorkspaceMdRecent() {
  try {
    localStorage.removeItem(RECENT_KEY)
  } catch {
    /* ignore */
  }
}

export function readWorkspaceMdPinned(): string[] {
  return readStringArray(PINNED_KEY)
}

/** Returns true if the path is pinned after the toggle. */
export function toggleWorkspaceMdPin(relPath: string): boolean {
  const p = relPath.trim()
  if (!p) return false
  const prev = readWorkspaceMdPinned()
  const i = prev.indexOf(p)
  let next: string[]
  if (i >= 0) {
    next = [...prev.slice(0, i), ...prev.slice(i + 1)]
  } else {
    next = [p, ...prev.filter((x) => x !== p)].slice(0, MAX_PINNED)
  }
  writeStringArray(PINNED_KEY, next)
  return i < 0
}

export function isWorkspaceMdPinned(relPath: string): boolean {
  const p = relPath.trim()
  if (!p) return false
  return readWorkspaceMdPinned().includes(p)
}
