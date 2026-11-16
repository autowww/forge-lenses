import { embedUrlForStaticPath } from './staticPreviewUrl'
import { normalizeStudioAppHref, stripStudioUrlPath } from './studioHrefResolve'

export { stripStudioUrlPath }

/** Leave as native navigation (API, dev assets, etc.). */
const PLAIN_HREF_PREFIXES = ['/api/', '/__ks/']

/**
 * Map a markdown `<a href>` to a React Router `to` value when the click should stay in Studio.
 * Returns `null` when the caller should render a plain `<a href>`.
 */
export function markdownHrefToStudioTo(
  href: string,
  pageOrigin: string = typeof window !== 'undefined' ? window.location.origin : '',
): string | null {
  const origin = pageOrigin || (typeof window !== 'undefined' ? window.location.origin : '')
  const h = normalizeStudioAppHref((href || '').trim(), origin)
  if (!h || h.startsWith('#')) return null
  if (/^mailto:|^tel:/i.test(h)) return null

  if (/^https?:\/\//i.test(h)) {
    try {
      const u = new URL(h)
      if (!origin || u.origin !== origin) return null
      const path = stripStudioUrlPath(u.pathname)
      return embedUrlForStaticPath(path + u.search + u.hash)
    } catch {
      return null
    }
  }

  if (h.startsWith('/')) {
    if (PLAIN_HREF_PREFIXES.some((pre) => h.startsWith(pre))) return null
    return embedUrlForStaticPath(h)
  }

  return null
}

export function isProbablyExternalHttpUrl(href: string): boolean {
  const t = (href || '').trim()
  return /^https?:\/\//i.test(t)
}
