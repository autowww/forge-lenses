import type { PortfolioHealth, RepoPortfolioRow } from './workspacePortfolio'

export type PortfolioSortKey =
  | 'name'
  | 'health'
  | 'riskScore'
  | 'standardsScore'
  | 'roadmapCount'
  | 'wbsCount'
  | 'linesAdded7d'
  | 'evidenceFlags'

export type SortDir = 'asc' | 'desc'

const healthOrder: Record<PortfolioHealth, number> = {
  at_risk: 0,
  watch: 1,
  healthy: 2,
}

function num(v: number | null | undefined): number {
  if (v == null || Number.isNaN(v)) return -Infinity
  return v
}

export function comparePortfolioRows(
  a: RepoPortfolioRow,
  b: RepoPortfolioRow,
  key: PortfolioSortKey,
  dir: SortDir,
): number {
  const m = dir === 'asc' ? 1 : -1
  switch (key) {
    case 'name':
      return m * a.name.localeCompare(b.name, undefined, { sensitivity: 'base' })
    case 'health':
      return m * (healthOrder[a.health] - healthOrder[b.health])
    case 'riskScore':
      return m * (a.riskScore - b.riskScore)
    case 'standardsScore':
      return m * (num(a.standardsScore) - num(b.standardsScore))
    case 'roadmapCount':
      return m * (a.roadmapCount - b.roadmapCount)
    case 'wbsCount':
      return m * (a.wbsCount - b.wbsCount)
    case 'linesAdded7d':
      return m * (num(a.linesAdded7d) - num(b.linesAdded7d))
    case 'evidenceFlags':
      return m * (a.evidenceFlags - b.evidenceFlags)
    default:
      return 0
  }
}

export function sortPortfolioRows(
  rows: RepoPortfolioRow[],
  key: PortfolioSortKey,
  dir: SortDir,
): RepoPortfolioRow[] {
  return [...rows].sort((a, b) => comparePortfolioRows(a, b, key, dir))
}

export function partitionByHealth(rows: RepoPortfolioRow[]): {
  at_risk: RepoPortfolioRow[]
  watch: RepoPortfolioRow[]
  healthy: RepoPortfolioRow[]
} {
  const at_risk: RepoPortfolioRow[] = []
  const watch: RepoPortfolioRow[] = []
  const healthy: RepoPortfolioRow[] = []
  for (const r of rows) {
    if (r.health === 'at_risk') at_risk.push(r)
    else if (r.health === 'watch') watch.push(r)
    else healthy.push(r)
  }
  return { at_risk, watch, healthy }
}
