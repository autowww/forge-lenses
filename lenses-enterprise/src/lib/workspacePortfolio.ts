import type { ForgeHint, WorkspaceChild, WorkspaceState } from '../api/workspace'
import type { OverviewChartPayload } from '../api/chartOverview'
import { linesAddedByRepo, perRepoLinesByKey } from '../api/chartOverview'
import { linesPrevByRepo } from './kpiTrendUi'

export type PortfolioHealth = 'healthy' | 'watch' | 'at_risk'

export type RepoPortfolioRow = {
  name: string
  health: PortfolioHealth
  riskScore: number
  standardsScore: number | null
  standardsTier: string | null
  dirty: boolean
  roadmapCount: number
  wbsCount: number
  linesAdded7d: number | null
  /** Lines added in the prior period of the same length (when chart API includes trends). */
  linesPrev7d: number | null
  /** Lines trend tier from API (`per_repo_lines`), for KPI-style coloring. */
  linesTier: string | null
  linesMedianPrior6: number | null
  evidenceFlags: number
  forgeHint: ForgeHint | null
}

function countForRepoHint(
  list: { repo_hint?: string }[] | undefined,
  repoName: string,
): number {
  if (!Array.isArray(list)) return 0
  return list.filter((x) => String(x.repo_hint ?? '').trim() === repoName).length
}

function findForgeHint(hints: ForgeHint[] | undefined, repoName: string): ForgeHint | null {
  if (!Array.isArray(hints)) return null
  const h = hints.find((x) => String(x.repo_hint ?? '').trim() === repoName)
  return h ?? null
}

function evidenceFlagCount(h: ForgeHint | null): number {
  if (!h) return 0
  let n = 0
  if (h.has_charge) n += 1
  if (h.has_journal) n += 1
  if (h.has_versona) n += 1
  if (h.has_ember_logs) n += 1
  return n
}

/** Higher = worse; used for sorting risk-first views. */
export function computeRiskScore(
  child: WorkspaceChild,
  roadmapCount: number,
  wbsCount: number,
  workspaceHasRoadmaps: boolean,
  workspaceHasWbs: boolean,
): number {
  let s = 0
  const dirty =
    child.is_git &&
    child.git &&
    (child.git as { dirty?: boolean }).dirty === true
  if (dirty) s += 4

  const sc = child.standards_compliance
  const score = sc && typeof sc.score === 'number' ? sc.score : null
  const tier = sc && typeof sc.tier === 'string' ? sc.tier : null
  if (tier === 'minimal') s += 3
  else if (score != null && score < 70) s += 3

  if (workspaceHasRoadmaps && roadmapCount === 0) s += 2
  if (workspaceHasWbs && wbsCount === 0) s += 2

  return s
}

export function classifyHealth(
  child: WorkspaceChild,
  roadmapCount: number,
  wbsCount: number,
  workspaceHasRoadmaps: boolean,
  workspaceHasWbs: boolean,
): { health: PortfolioHealth; riskScore: number } {
  const riskScore = computeRiskScore(
    child,
    roadmapCount,
    wbsCount,
    workspaceHasRoadmaps,
    workspaceHasWbs,
  )

  const dirty =
    child.is_git &&
    child.git &&
    (child.git as { dirty?: boolean }).dirty === true
  const sc = child.standards_compliance
  const score = sc && typeof sc.score === 'number' ? sc.score : null
  const tier = sc && typeof sc.tier === 'string' ? sc.tier : null

  const atRisk =
    dirty === true ||
    tier === 'minimal' ||
    (score != null && score < 70)

  if (atRisk) return { health: 'at_risk', riskScore }

  const watch =
    (workspaceHasRoadmaps && roadmapCount === 0) ||
    (workspaceHasWbs && wbsCount === 0)

  if (watch) return { health: 'watch', riskScore }

  return { health: 'healthy', riskScore }
}

export function buildRepoPortfolioRows(
  state: WorkspaceState | null,
  chartPayload: OverviewChartPayload | null,
): RepoPortfolioRow[] {
  if (!state) return []
  const children = Array.isArray(state.children) ? state.children : []
  const gitRepos = children.filter((c) => c.is_git)
  const linesMap = chartPayload ? linesAddedByRepo(chartPayload) : new Map<string, number>()
  const prevMap = chartPayload ? linesPrevByRepo(chartPayload) : new Map<string, number>()
  const linesTierMap = chartPayload ? perRepoLinesByKey(chartPayload) : new Map()

  const workspaceHasRoadmaps = (state.roadmaps?.length ?? 0) > 0
  const workspaceHasWbs = (state.wbs?.length ?? 0) > 0
  const hints = state.forge_hints

  const rows: RepoPortfolioRow[] = []
  for (const ch of gitRepos) {
    const name = String(ch.name ?? '').trim()
    if (!name) continue

    const nameKey = name.toLowerCase()
    const prLines = linesTierMap.get(nameKey)
    const roadmapCount = countForRepoHint(state.roadmaps, name)
    const wbsCount = countForRepoHint(state.wbs, name)
    const { health, riskScore } = classifyHealth(
      ch,
      roadmapCount,
      wbsCount,
      workspaceHasRoadmaps,
      workspaceHasWbs,
    )

    const sc = ch.standards_compliance
    const fh = findForgeHint(hints, name)

    rows.push({
      name,
      health,
      riskScore,
      standardsScore: sc && typeof sc.score === 'number' ? sc.score : null,
      standardsTier: sc && typeof sc.tier === 'string' ? sc.tier : null,
      dirty: Boolean(
        ch.is_git && ch.git && (ch.git as { dirty?: boolean }).dirty === true,
      ),
      roadmapCount,
      wbsCount,
      linesAdded7d: linesMap.has(nameKey) ? linesMap.get(nameKey)! : null,
      linesPrev7d: prevMap.has(nameKey) ? prevMap.get(nameKey)! : null,
      linesTier: prLines?.tier != null ? String(prLines.tier) : null,
      linesMedianPrior6:
        typeof prLines?.median_prior_6 === 'number' || prLines?.median_prior_6 === null
          ? prLines.median_prior_6
          : null,
      evidenceFlags: evidenceFlagCount(fh),
      forgeHint: fh,
    })
  }

  rows.sort((a, b) => b.riskScore - a.riskScore || a.name.localeCompare(b.name))
  return rows
}

export type WinRepo = {
  name: string
  linesAdded7d: number
}

/** Repos with healthy classification, clean tree, and measurable 7d activity. */
export function pickRecentWins(rows: RepoPortfolioRow[], limit: number): WinRepo[] {
  const wins = rows
    .filter(
      (r) =>
        r.health === 'healthy' &&
        !r.dirty &&
        r.linesAdded7d != null &&
        r.linesAdded7d > 0,
    )
    .sort((a, b) => (b.linesAdded7d ?? 0) - (a.linesAdded7d ?? 0))
    .slice(0, limit)
    .map((r) => ({ name: r.name, linesAdded7d: r.linesAdded7d ?? 0 }))
  return wins
}

export function anyChargeArtifact(state: WorkspaceState | null): boolean {
  const hints = state?.forge_hints
  if (!Array.isArray(hints)) return false
  return hints.some((h) => h.has_charge)
}
