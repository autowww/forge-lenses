import type { WorkspaceState } from '../api/workspace'

/** True when the scan looks like a single-repo or empty workspace (crawl v2 sparse pattern). */
export function isWorkspaceSparse(state: WorkspaceState | null | undefined): boolean {
  if (!state) return false
  const children = Array.isArray(state.children) ? state.children : []
  const gitRepos = children.filter((c) => c.is_git).length
  const wbs = (state.wbs ?? []).length
  const roadmaps = (state.roadmaps ?? []).length
  return children.length <= 1 || (wbs === 0 && roadmaps === 0 && gitRepos <= 1)
}
