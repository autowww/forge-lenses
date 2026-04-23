/**
 * Primary cookie: workspace_lens=flow|artifacts.
 * Migrates legacy nav_mode on read.
 */
export const WORKSPACE_LENS_COOKIE = 'workspace_lens'
export const LEGACY_NAV_MODE_COOKIE = 'nav_mode'

export type WorkspaceLens = 'flow' | 'artifacts'
export type NavMode = WorkspaceLens

const VALID: ReadonlySet<string> = new Set(['flow', 'artifacts'])
const MAX_AGE = 31536000

function readCookieRaw(name: string): string {
  if (typeof document === 'undefined') return ''
  const m = document.cookie.match(
    new RegExp('(?:^|; )' + name.replace(/[-[\]{}()*+?.\\^$|]/g, '\\$&') + '=([^;]*)'),
  )
  return m ? decodeURIComponent(m[1].trim()) : ''
}

export function readWorkspaceLens(): WorkspaceLens | null {
  let v = readCookieRaw(WORKSPACE_LENS_COOKIE)
  if (!VALID.has(v)) v = readCookieRaw(LEGACY_NAV_MODE_COOKIE)
  if (VALID.has(v)) return v as WorkspaceLens
  return null
}

export function writeWorkspaceLens(mode: WorkspaceLens): void {
  if (typeof document === 'undefined') return
  const secure = typeof location !== 'undefined' && location.protocol === 'https:' ? '; Secure' : ''
  document.cookie = `${WORKSPACE_LENS_COOKIE}=${encodeURIComponent(mode)}; Path=/; Max-Age=${MAX_AGE}; SameSite=Lax${secure}`
}

/** @deprecated use readWorkspaceLens */
export function readNavMode(): WorkspaceLens | null {
  return readWorkspaceLens()
}

/** @deprecated use writeWorkspaceLens */
export function writeNavMode(mode: WorkspaceLens): void {
  writeWorkspaceLens(mode)
}

export const NAV_MODE_COOKIE = WORKSPACE_LENS_COOKIE
