import { embedUrlForStaticPath } from './staticPreviewUrl'
import { normalizeStudioAppHref, stripStudioUrlPath } from './studioHrefResolve'

/**
 * Pathnames (after /studio strip and /docs → /view rewrite) that the Studio SPA serves.
 * Anything else keeps default browser navigation (Classic-only pages like /roadmaps/summary).
 */
const SPA_PATH_PREFIXES = [
  '/plan',
  '/wbs',
  '/projects',
  '/timeline',
  '/board',
  '/websites',
  '/search',
  '/chat',
  '/settings',
  '/toolset',
  '/overview',
  '/tutorials',
  '/blog',
  '/view',
  '/workspace-md',
  '/roadmap-section',
  '/feature-showcase',
  '/blueprints',
  '/knowledge',
  '/governance',
] as const

export function isSpaHandledPathname(pathOnly: string): boolean {
  const p = pathOnly.split('?')[0]?.split('#')[0] ?? ''
  if (p === '/' || p === '') return true
  for (const pre of SPA_PATH_PREFIXES) {
    if (p === pre || p.startsWith(`${pre}/`)) return true
  }
  return false
}

const SKIP_PREFIXES = ['/api/', '/__ks/']

/**
 * If this same-document anchor should be handled by React Router, return the `to` string
 * (basename-relative, e.g. `/plan?tab=story`). Otherwise `null` (full navigation / download / Classic).
 */
export function hrefToStudioRouterTo(
  hrefAttr: string,
  pageOrigin: string = typeof window !== 'undefined' ? window.location.origin : '',
): string | null {
  const origin = pageOrigin || (typeof window !== 'undefined' ? window.location.origin : '')
  const raw = (hrefAttr || '').trim()
  if (!raw || raw.startsWith('#')) return null
  if (/^javascript:|^data:|^blob:/i.test(raw)) return null
  if (/^mailto:|^tel:/i.test(raw)) return null

  const norm = normalizeStudioAppHref(raw, origin)

  if (/^https?:\/\//i.test(norm)) {
    try {
      const u = new URL(norm)
      if (u.origin !== origin) return null
    } catch {
      return null
    }
  }

  if (!norm.startsWith('/')) return null

  let url: URL
  try {
    url = new URL(norm, origin + '/')
  } catch {
    return null
  }

  if (url.origin !== origin) return null

  let path = url.pathname
  if (path === '/studio' || path.startsWith('/studio/')) {
    path = stripStudioUrlPath(path)
  }

  if (SKIP_PREFIXES.some((pre) => path.startsWith(pre))) return null

  const pathSearchHash = path + url.search + url.hash
  const mapped = embedUrlForStaticPath(pathSearchHash)

  let checkPath: string
  try {
    checkPath = new URL(mapped, origin + '/').pathname
  } catch {
    return null
  }

  if (!isSpaHandledPathname(checkPath)) return null
  return mapped
}
