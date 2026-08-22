/**
 * Workspace-relative markdown paths the SDLC copilot may load as grounding sources.
 * Server resolves only allowlisted paths (see lenses.safe_forge_paths).
 */

/** Typical charge log locations for a named repo / project folder or workspace root. */
export function chargeMdCandidates(repoOrProjectSlug?: string | null): string[] {
  const s = (repoOrProjectSlug || '').trim()
  const uniq: string[] = []
  const push = (p: string) => {
    const t = p.trim()
    if (t && !uniq.includes(t)) uniq.push(t)
  }
  if (s) push(`${s}/forge/charge.md`)
  push('forge/charge.md')
  return uniq
}

/** Dedupe and cap paths before POST /api/sdlc-copilot/chat. */
export function compactRelatedMdPathsForApi(paths: string[] | undefined, max = 10): string[] | undefined {
  if (!paths?.length) return undefined
  const out: string[] = []
  const seen = new Set<string>()
  for (const p of paths) {
    const t = typeof p === 'string' ? p.trim() : ''
    if (!t || seen.has(t)) continue
    seen.add(t)
    out.push(t)
    if (out.length >= max) break
  }
  return out.length ? out : undefined
}
