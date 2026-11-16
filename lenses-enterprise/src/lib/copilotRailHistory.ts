/**
 * Persist Lenses Copilot rail messages in localStorage (per workspace + page route).
 * Survives closing and reopening Forge Studio in the same browser profile.
 */

type CopilotRailBundleV1 = {
  v: 1
  routes: Record<
    string,
    {
      messages: unknown[]
      updatedAt: number
    }
  >
}

const STORAGE_BASE = 'lenses.studio.copilot_rail_bundle_v1'

function storageKey(workspaceRoot: string | undefined | null): string {
  const w = (workspaceRoot || '').trim()
  if (!w) return STORAGE_BASE
  return `${STORAGE_BASE}::${encodeURIComponent(w)}`
}

function normalizeRouteKey(route: string): string {
  const r = (route || 'default').trim() || 'default'
  return r.slice(0, 280)
}

function emptyBundle(): CopilotRailBundleV1 {
  return { v: 1, routes: {} }
}

function readBundle(workspaceRoot: string | undefined | null): CopilotRailBundleV1 {
  try {
    const raw = localStorage.getItem(storageKey(workspaceRoot))
    if (!raw) return emptyBundle()
    const o = JSON.parse(raw) as unknown
    if (!o || typeof o !== 'object') return emptyBundle()
    const rec = o as Record<string, unknown>
    if (rec.v !== 1 || typeof rec.routes !== 'object' || !rec.routes) return emptyBundle()
    return { v: 1, routes: rec.routes as CopilotRailBundleV1['routes'] }
  } catch {
    return emptyBundle()
  }
}

function isMessageRow(x: unknown): boolean {
  if (!x || typeof x !== 'object') return false
  const r = x as Record<string, unknown>
  const role = r.role
  if (role !== 'user' && role !== 'assistant') return false
  return typeof r.text === 'string'
}

/** Restore persisted rail messages for this workspace and Studio route. */
export function readCopilotRailMessages(
  workspaceRoot: string | undefined | null,
  route: string,
): unknown[] {
  const key = normalizeRouteKey(route)
  const row = readBundle(workspaceRoot).routes[key]
  const arr = row?.messages
  if (!Array.isArray(arr)) return []
  return arr.filter(isMessageRow)
}

/** Save rail messages for this workspace and Studio route. */
export function writeCopilotRailMessages(
  workspaceRoot: string | undefined | null,
  route: string,
  messages: unknown[],
): void {
  try {
    const bundle = readBundle(workspaceRoot)
    const key = normalizeRouteKey(route)
    bundle.routes[key] = {
      messages,
      updatedAt: Date.now(),
    }
    localStorage.setItem(storageKey(workspaceRoot), JSON.stringify(bundle))
  } catch {
    /* quota or private mode */
  }
}
