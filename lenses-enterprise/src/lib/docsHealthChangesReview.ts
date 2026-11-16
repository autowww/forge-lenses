import type { DocsHealthCluster, DocsHealthFinding, DocsHealthSessionPayload } from '../api/docsHealth'

/** Human-readable risk for approval (no raw severity codes in UI labels). */
export function deriveApprovalRiskLevel(
  finding?: DocsHealthFinding | null,
  cluster?: Pick<DocsHealthCluster, 'primary_severity'> | null,
): string {
  const s = String(finding?.severity || cluster?.primary_severity || '').toLowerCase()
  if (!s.trim()) return 'Not classified'
  if (s.includes('critical') || s.includes('blocker') || s.includes('p0')) return 'High'
  if (s.includes('major') || s.includes('high') || s.includes('p1')) return 'High'
  if (s.includes('medium') || s.includes('moderate') || s.includes('p2')) return 'Medium'
  if (s.includes('minor') || s.includes('low') || s.includes('info') || s.includes('p3')) return 'Low'
  return 'Not classified'
}

function kindLabel(kind?: string | null): string {
  const k = String(kind || '').toLowerCase()
  if (k === 'diagram') return 'diagram update'
  if (k === 'adr' || k === 'decision') return 'decision record'
  if (k === 'markdown' || k === 'patch' || k === '') return 'documentation update'
  return k.replace(/_/g, ' ') || 'documentation update'
}

/** One-line description of the proposed change surface for reviewers. */
export function describeWhatWillChange(session: DocsHealthSessionPayload | null): string {
  if (!session) return 'Not available'
  const path = session.proposed_patch?.path || session.remediation_scope?.proposed_patch_path
  const kind = session.proposed_patch_kind || session.remediation_scope?.proposed_patch_kind
  const base = kindLabel(kind)
  if (path) return `${base} targeting ${path}`
  return `Proposed ${base}`
}

export function countAffectedPathsForChanges(session: DocsHealthSessionPayload | null): number | null {
  const scope = session?.remediation_scope
  if (!scope) return null
  if (typeof scope.distinct_path_count === 'number') return scope.distinct_path_count
  const paths = scope.distinct_affected_paths
  if (paths?.length) return paths.length
  return null
}

export function describeApplyStrategy(session: DocsHealthSessionPayload | null): string {
  if (!session) return 'Not available'
  const b = session.suggested_git_branch?.trim()
  if (b) return `Branch-first apply to ${b} (recommended)`
  return 'Apply to the repository default branch — confirm policy with your team before approving.'
}
