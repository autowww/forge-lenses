/** Split a stored thread key (`pathname` + optional `search`) back for nav + titles. */
export function splitThreadKey(threadKey: string): { pathname: string; search: string } {
  const k = threadKey.trim() || '/'
  const q = k.indexOf('?')
  if (q < 0) return { pathname: k || '/', search: '' }
  return { pathname: k.slice(0, q) || '/', search: k.slice(q) }
}
