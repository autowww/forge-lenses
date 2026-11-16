import { Navigate, useParams } from 'react-router-dom'

/** Canonical redirect from legacy `/view/local-site/…` to `/websites/browse/:site/…`. */
export function LocalSiteRedirect() {
  const splat = (useParams()['*'] ?? '').trim()
  const parts = splat.replace(/^\/+/, '').split('/').filter(Boolean)
  const site = parts[0]
  if (!site) {
    return <Navigate to="/websites" replace />
  }
  const tail = parts.slice(1).join('/')
  const dest = `/websites/browse/${encodeURIComponent(site)}${tail ? `/${tail}` : ''}`
  return <Navigate to={dest} replace />
}
