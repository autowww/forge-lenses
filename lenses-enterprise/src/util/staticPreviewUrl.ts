/** Studio in-app routes that wrap `/docs` and `/local-site` with the shell + iframe. */
export const STUDIO_DOCS_HOME = '/view/docs'

/**
 * Map API or indexed URLs (`/docs/…`, `/local-site/…`) to Studio shell routes (`/view/…`)
 * so navigation stays inside the SPA.
 */
export function embedUrlForStaticPath(url: string): string {
  const u = (url || '').trim()
  if (!u) return u
  const q = u.indexOf('?')
  const h = u.indexOf('#')
  let end = u.length
  if (q >= 0) end = Math.min(end, q)
  if (h >= 0) end = Math.min(end, h)
  const path = u.slice(0, end)
  const suffix = u.slice(end)

  if (path === '/docs' || path.startsWith('/docs/')) {
    const tail = path.slice('/docs'.length).replace(/^\//, '')
    return '/view/docs' + (tail ? '/' + tail : '') + suffix
  }
  if (path.startsWith('/local-site/')) {
    return '/view' + path + suffix
  }
  return u
}
