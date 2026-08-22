/**
 * Resolve Studio in-app URLs: relative links must use the SPA root (/studio/), not the
 * current path. Otherwise `plan?…` from `/studio/wbs/view` becomes `/studio/wbs/plan`
 * (no route → blank / redirect home).
 */

export function stripStudioUrlPath(pathname: string): string {
  if (pathname === '/studio') return '/'
  if (pathname.startsWith('/studio/')) {
    const rest = pathname.slice('/studio'.length)
    return rest.startsWith('/') ? rest : `/${rest}`
  }
  return pathname
}

/** Turn `plan?tab=1` into `/studio/plan?tab=1` using Vite `base` (SPA root). */
export function expandRelativeStudioHref(href: string): string {
  const t = (href || '').trim()
  if (!t) return t
  if (t.startsWith('/') || /^https?:\/\//i.test(t) || t.startsWith('#')) return t
  if (/^mailto:|^tel:/i.test(t)) return t
  if (typeof window === 'undefined') return t
  try {
    const base = `${window.location.origin}${import.meta.env.BASE_URL || '/studio/'}`
    const u = new URL(t, base)
    return u.pathname + u.search + u.hash
  } catch {
    return t
  }
}

/**
 * Relative → absolute under `/studio/`, then strip `/studio` prefix for router `to` strings.
 * Same-origin absolute URLs also get `/studio` stripped from pathname.
 */
export function normalizeStudioAppHref(href: string, pageOrigin: string): string {
  const expanded = expandRelativeStudioHref(href)
  if (!pageOrigin) return expanded
  try {
    if (/^https?:\/\//i.test(expanded)) {
      const u = new URL(expanded)
      if (u.origin !== pageOrigin) return expanded
      let p = u.pathname
      if (p === '/studio' || p.startsWith('/studio/')) {
        p = stripStudioUrlPath(p)
      }
      return p + u.search + u.hash
    }
    if (expanded.startsWith('/')) {
      const u = new URL(expanded, pageOrigin + '/')
      let p = u.pathname
      if (p === '/studio' || p.startsWith('/studio/')) {
        p = stripStudioUrlPath(p)
      }
      return p + u.search + u.hash
    }
    return expanded
  } catch {
    return expanded
  }
}
