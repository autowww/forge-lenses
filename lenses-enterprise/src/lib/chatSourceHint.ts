/** Short locator for chat source rows (repo tail, project slug, notable query keys). */
export function buildChatSourceHint(
  pathname: string,
  search: string,
  workspaceRoot: string | undefined | null,
): string {
  const parts: string[] = []
  const root = (workspaceRoot || '').trim()
  if (root) {
    const segments = root.split('/').filter(Boolean)
    const tail = segments.slice(-2).join('/')
    if (tail) parts.push(`Workspace · ${tail}`)
  }
  const m = pathname.match(/^\/projects\/([^/]+)/)
  if (m) parts.push(`Project · ${decodeURIComponent(m[1])}`)
  const qs = search.startsWith('?') ? search.slice(1) : search
  if (qs) {
    const sp = new URLSearchParams(qs)
    const tab = sp.get('tab')
    if (tab) parts.push(`tab=${tab}`)
  }
  if (parts.length === 0 && pathname) parts.push(pathname)
  return parts.join(' · ')
}
