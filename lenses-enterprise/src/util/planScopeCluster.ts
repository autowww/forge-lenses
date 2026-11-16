import { friendlyDocumentTitle, friendlyRepoLabel } from './planDisplayNames'

export type WithRepoPath = { rel_path: string; repo_hint?: string }

export type RepoCluster<T extends WithRepoPath> = {
  repoHint: string
  items: T[]
}

/** Group WBS/roadmap rows by `repo_hint` (one product/repo per cluster). */
export function clusterByRepoHint<T extends WithRepoPath>(items: T[]): RepoCluster<T>[] {
  const map = new Map<string, T[]>()
  for (const it of items) {
    const h = (it.repo_hint || '').trim()
    const key = h || '__root__'
    if (!map.has(key)) map.set(key, [])
    map.get(key)!.push(it)
  }
  return [...map.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([repoHint, groupItems]) => ({
      repoHint,
      items: [...groupItems].sort((x, y) => x.rel_path.localeCompare(y.rel_path)),
    }))
}

export function clusterHeadingLabel(repoHint: string): string {
  if (!repoHint || repoHint === '__root__') return 'Workspace root'
  return friendlyRepoLabel(repoHint)
}

/**
 * Human line for a backlog row: location inside the product folder, no “Markdown” boilerplate
 * and no `.md` / trailing `WBS` filename noise when it is the default file name.
 */
export function wbsBacklogPickerLabel(relPath: string, repoHint: string): string {
  let tail = (relPath || '').trim().replace(/\\/g, '/')
  const rh = (repoHint || '').trim()
  if (rh && tail.startsWith(`${rh}/`)) {
    tail = tail.slice(rh.length + 1)
  }
  tail = tail.replace(/\.(md|markdown)$/i, '')
  const parts = tail.split('/').filter(Boolean)
  if (parts.length && /^wbs$/i.test(parts[parts.length - 1]!)) {
    parts.pop()
  }
  if (parts.length === 0) return 'Backlog'
  return parts
    .map((seg) =>
      seg
        .replace(/[-_]+/g, ' ')
        .replace(/\b\w/g, (c) => c.toUpperCase()),
    )
    .join(' › ')
}

export function roadmapVariantSubtitle(relPath: string): string {
  const base = friendlyDocumentTitle(relPath)
  return base.toLowerCase() === 'roadmap' ? 'Release narrative' : base
}

/**
 * Path under the product folder (after `repo_hint/`), without `ROADMAP.md` — tells nested roadmaps apart.
 */
export function roadmapLocationLabel(relPath: string, repoHint: string): string {
  const norm = relPath.replace(/\\/g, '/')
  const p = (repoHint || '').trim()
  let tail = norm
  if (p && norm.startsWith(`${p}/`)) tail = norm.slice(p.length + 1)
  tail = tail.replace(/\/?ROADMAP\.md$/i, '')
  if (!tail) return 'Repository root'
  return tail.split('/').join(' › ')
}

/** `repo_hint` for the currently selected WBS row, if any. */
export function repoHintForWbsPath(wbsList: WithRepoPath[], wbsP: string): string {
  const row = wbsList.find((w) => w.rel_path === wbsP)
  return (row?.repo_hint || '').trim()
}

export function filterRoadmapsForRepoHint<T extends WithRepoPath>(
  roadmaps: T[],
  repoHint: string,
): T[] {
  const h = repoHint.trim()
  if (!h) return roadmaps
  return roadmaps.filter((r) => (r.repo_hint || '').trim() === h)
}
