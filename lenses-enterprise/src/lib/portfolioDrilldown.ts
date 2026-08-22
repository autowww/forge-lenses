import type { RepoPortfolioRow } from './workspacePortfolio'

/** Query `?filter=` on `/projects` (artifacts table + flow card grid). */
export type PortfolioTableFilter = 'all' | 'attention' | 'dirty' | 'evidence'

export function parsePortfolioTableFilter(raw: string | null | undefined): PortfolioTableFilter {
  if (raw === 'attention' || raw === 'dirty' || raw === 'evidence') return raw
  return 'all'
}

export function filterPortfolioRows(
  rows: RepoPortfolioRow[],
  filter: PortfolioTableFilter,
): RepoPortfolioRow[] {
  if (filter === 'all') return rows
  if (filter === 'attention') return rows.filter((r) => r.health === 'at_risk' || r.health === 'watch')
  if (filter === 'dirty') return rows.filter((r) => r.dirty)
  if (filter === 'evidence') return rows.filter((r) => r.evidenceFlags > 0)
  return rows
}
