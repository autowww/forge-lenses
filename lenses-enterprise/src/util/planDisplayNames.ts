/** Human-facing label from a repo-relative document path (WBS / roadmap). */
export function friendlyDocumentTitle(relPath: string): string {
  const t = (relPath || '').trim().replace(/\\/g, '/')
  if (!t) return ''
  const seg = t.split('/').filter(Boolean)
  const base = seg[seg.length - 1] ?? t
  return base
    .replace(/\.(md|markdown|csv)$/i, '')
    .replace(/[-_]+/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

/** Short repo / product label (folder name, not full path). */
export function friendlyRepoLabel(repoHint: string): string {
  const t = (repoHint || '').trim().replace(/\\/g, '/')
  if (!t) return ''
  const parts = t.split('/').filter(Boolean)
  return parts[parts.length - 1] ?? t
}
