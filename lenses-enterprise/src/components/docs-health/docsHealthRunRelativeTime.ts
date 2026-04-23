/** Short relative / time label for compact run summaries. */
export function formatRunStartedShort(iso?: string): string {
  if (!iso) return ''
  const t = Date.parse(iso)
  if (Number.isNaN(t)) return ''
  const sec = Math.max(0, Math.floor((Date.now() - t) / 1000))
  if (sec < 45) return 'just now'
  if (sec < 3600) return `${Math.floor(sec / 60)}m ago`
  if (sec < 86400) return `${Math.floor(sec / 3600)}h ago`
  try {
    return new Date(t).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })
  } catch {
    return ''
  }
}
