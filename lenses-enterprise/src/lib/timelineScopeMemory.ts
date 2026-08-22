const STORAGE_KEY = 'lenses.timeline.persistedScope'

export type PersistedTimelineScope = {
  repo?: string
  wbs_p?: string
  roadmap_p?: string
}

export function readPersistedScope(): PersistedTimelineScope | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as PersistedTimelineScope
    if (!parsed || typeof parsed !== 'object') return null
    return parsed
  } catch {
    return null
  }
}

/** Remember last repo / WBS / roadmap picks for Timeline (human labels stored separately when needed). */
export function rememberScope(scope: PersistedTimelineScope): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(scope))
  } catch {
    /* quota / private mode */
  }
}

export function lastScopeFromParams(repo: string, wbsP: string, roadmapP: string): PersistedTimelineScope {
  return {
    repo: repo.trim() || undefined,
    wbs_p: wbsP.trim() || undefined,
    roadmap_p: roadmapP.trim() || undefined,
  }
}
