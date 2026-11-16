import type {
  ForgeHint,
  WorkspaceChild,
  WorkspaceState,
  WorkspaceWebsite,
} from '../api/workspace'

export const SITE_INDEX_STALE_DAYS = 90

export type SitePortfolioRow = {
  site: WorkspaceWebsite
  coverageGap: boolean
  staleIndex: boolean
  roadmapCount: number
  wbsCount: number
  forgeHint: ForgeHint | null
  child: WorkspaceChild | undefined
}

export function hasCoverageGap(w: WorkspaceWebsite): boolean {
  const t = w.html_total ?? 0
  const i = w.html_indexed ?? 0
  if (t <= 0) return false
  return i < t
}

/** `index_html_mtime` is Unix seconds (Python st_mtime). */
export function isIndexStale(
  w: WorkspaceWebsite,
  now: Date,
  staleDays: number = SITE_INDEX_STALE_DAYS,
): boolean {
  const m = w.index_html_mtime
  if (m == null || Number.isNaN(Number(m))) return true
  const sec = typeof m === 'number' ? m : parseFloat(String(m))
  if (Number.isNaN(sec)) return true
  const ms = sec * 1000
  const ageMs = now.getTime() - ms
  return ageMs > staleDays * 24 * 60 * 60 * 1000
}

export function formatIndexMtime(m: number | null | undefined): string {
  if (m == null || Number.isNaN(Number(m))) return '—'
  const sec = typeof m === 'number' ? m : parseFloat(String(m))
  if (Number.isNaN(sec)) return '—'
  try {
    return new Date(sec * 1000).toLocaleString(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short',
    })
  } catch {
    return '—'
  }
}

export function countRoadmapsForRepo(state: WorkspaceState | null, repoName: string): number {
  const roadmaps = state?.roadmaps ?? []
  return roadmaps.filter((r) => String(r.repo_hint ?? '').trim() === repoName).length
}

export function countWbsForRepo(state: WorkspaceState | null, repoName: string): number {
  const wbs = state?.wbs ?? []
  return wbs.filter((x) => String(x.repo_hint ?? '').trim() === repoName).length
}

export function findForgeHintForRepo(state: WorkspaceState | null, repoName: string): ForgeHint | null {
  const hints = state?.forge_hints ?? []
  return hints.find((h) => String(h.repo_hint ?? '').trim() === repoName) ?? null
}

export function findChildByName(
  state: WorkspaceState | null,
  name: string,
): WorkspaceChild | undefined {
  return (state?.children ?? []).find((c) => c.name === name)
}

export function buildSitePortfolioRows(state: WorkspaceState | null, now: Date): SitePortfolioRow[] {
  const sites = (state?.websites ?? []) as WorkspaceWebsite[]
  const rows: SitePortfolioRow[] = []
  for (const site of sites) {
    const name = String(site.name ?? '').trim()
    if (!name) continue
    rows.push({
      site,
      coverageGap: hasCoverageGap(site),
      staleIndex: isIndexStale(site, now),
      roadmapCount: countRoadmapsForRepo(state, name),
      wbsCount: countWbsForRepo(state, name),
      forgeHint: findForgeHintForRepo(state, name),
      child: findChildByName(state, name),
    })
  }
  return rows
}

export type SiteSortKey =
  | 'name'
  | 'coverage'
  | 'mtime'
  | 'roadmapCount'
  | 'firebase_site_id'
  | 'html_total'

export type SortDir = 'asc' | 'desc'

function coverageRatio(row: SitePortfolioRow): number {
  const t = row.site.html_total ?? 0
  const i = row.site.html_indexed ?? 0
  if (t <= 0) return 1
  return i / t
}

function mtimeNum(row: SitePortfolioRow): number {
  const m = row.site.index_html_mtime
  if (m == null || Number.isNaN(Number(m))) return -Infinity
  const sec = typeof m === 'number' ? m : parseFloat(String(m))
  return Number.isNaN(sec) ? -Infinity : sec
}

export function compareSiteRows(
  a: SitePortfolioRow,
  b: SitePortfolioRow,
  key: SiteSortKey,
  dir: SortDir,
): number {
  const m = dir === 'asc' ? 1 : -1
  switch (key) {
    case 'name':
      return m * a.site.name.localeCompare(b.site.name, undefined, { sensitivity: 'base' })
    case 'coverage':
      return m * (coverageRatio(a) - coverageRatio(b))
    case 'mtime':
      return m * (mtimeNum(a) - mtimeNum(b))
    case 'roadmapCount':
      return m * (a.roadmapCount - b.roadmapCount)
    case 'firebase_site_id':
      return m * (a.site.firebase_site_id || '').localeCompare(b.site.firebase_site_id || '')
    case 'html_total':
      return m * ((a.site.html_total ?? 0) - (b.site.html_total ?? 0))
    default:
      return 0
  }
}

export function sortSiteRows(
  rows: SitePortfolioRow[],
  key: SiteSortKey,
  dir: SortDir,
): SitePortfolioRow[] {
  return [...rows].sort((a, b) => compareSiteRows(a, b, key, dir))
}

/** Short derived bullets for the Sites hub (scan-only; no deploy API). */
export function siteAttentionBullets(state: WorkspaceState | null, now: Date): string[] {
  const rows = buildSitePortfolioRows(state, now)
  const bullets: string[] = []
  const cov = rows.filter((r) => r.coverageGap).length
  const st = rows.filter((r) => r.staleIndex).length
  const workspaceRoadmaps = (state?.roadmaps ?? []).length
  if (cov > 0) {
    bullets.push(
      `${cov} site(s) have more HTML files than the preview index lists — coverage may look worse than reality until indexing catches up.`,
    )
  }
  if (st > 0) {
    bullets.push(
      `${st} site(s) have a missing or stale index.html timestamp — verify publishing and rebuild output.`,
    )
  }
  if (workspaceRoadmaps > 0) {
    const noRm = rows.filter((r) => r.roadmapCount === 0).length
    if (noRm > 0 && rows.length > 0) {
      bullets.push(
        `${noRm} site repo(s) have no roadmap file indexed under that name — check ROADMAP paths or repo_hint alignment.`,
      )
    }
  }
  if (rows.length === 0) {
    bullets.push('No Firebase hosting roots detected in this workspace scan.')
    return bullets
  }
  if (bullets.length === 0) {
    bullets.push(
      'No blocking scan signals for sites — keep release notes and live URLs aligned in registry when you ship.',
    )
  }
  return bullets.slice(0, 5)
}
