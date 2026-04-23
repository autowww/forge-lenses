import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import type { WorkspaceChild } from '../../api/workspace'
import type { RepoPortfolioRow } from '../../lib/workspacePortfolio'
import {
  type PortfolioSortKey,
  type SortDir,
  partitionByHealth,
  sortPortfolioRows,
} from '../../lib/portfolioTableSort'
import {
  type PortfolioTableFilter,
  filterPortfolioRows,
} from '../../lib/portfolioDrilldown'
import { FULL_WORKSPACE_UI, STUDIO_VOCAB } from '../../nav/studioVisibleCopy'

function healthBadgeClass(health: RepoPortfolioRow['health']): string {
  switch (health) {
    case 'healthy':
      return 'le-cc-health le-cc-health--healthy'
    case 'watch':
      return 'le-cc-health le-cc-health--watch'
    case 'at_risk':
      return 'le-cc-health le-cc-health--at-risk'
    default:
      return 'le-cc-health'
  }
}

function healthLabel(health: RepoPortfolioRow['health']): string {
  switch (health) {
    case 'healthy':
      return 'Healthy'
    case 'watch':
      return 'Watch'
    case 'at_risk':
      return 'At risk'
    default:
      return health
  }
}

type Props = {
  rows: RepoPortfolioRow[]
  childByName: Map<string, WorkspaceChild>
  /** From `?filter=` on `/projects` (artifacts lens). */
  initialFilter?: PortfolioTableFilter
}

const COLUMNS: { key: PortfolioSortKey; label: string }[] = [
  { key: 'name', label: 'Repository' },
  { key: 'health', label: 'Health' },
  { key: 'riskScore', label: 'Risk' },
  { key: 'standardsScore', label: 'Standards' },
  { key: 'roadmapCount', label: 'Roadmaps' },
  { key: 'wbsCount', label: 'WBS' },
  { key: 'linesAdded7d', label: '7d lines' },
  { key: 'evidenceFlags', label: 'Evidence' },
]

export function PortfolioProjectsTable({ rows, childByName, initialFilter = 'all' }: Props) {
  const [filter, setFilter] = useState<PortfolioTableFilter>(initialFilter)
  const [sortKey, setSortKey] = useState<PortfolioSortKey>('riskScore')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})

  useEffect(() => {
    setFilter(initialFilter)
  }, [initialFilter])

  const filtered = useMemo(() => filterPortfolioRows(rows, filter), [rows, filter])

  const sorted = useMemo(
    () => sortPortfolioRows(filtered, sortKey, sortDir),
    [filtered, sortKey, sortDir],
  )

  const grouped = useMemo(() => partitionByHealth(sorted), [sorted])

  function toggleSort(key: PortfolioSortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir(key === 'name' ? 'asc' : 'desc')
    }
  }

  function toggleExpand(name: string) {
    setExpanded((e) => ({ ...e, [name]: !e[name] }))
  }

  const attentionCount = rows.filter((r) => r.health === 'at_risk' || r.health === 'watch').length
  const dirtyCount = rows.filter((r) => r.dirty).length
  const evidenceCount = rows.filter((r) => r.evidenceFlags > 0).length

  if (rows.length === 0) {
    return <p className="le-portfolio-empty">No git repositories in this workspace.</p>
  }

  if (sorted.length === 0) {
    return (
      <section className="le-portfolio-section" aria-labelledby="le-portfolio-table-h">
        <div className="le-portfolio-table-toolbar">
          <h2 id="le-portfolio-table-h" className="le-portfolio-section__title">
            Health and confidence
          </h2>
          <div className="le-portfolio-filters" role="group" aria-label="Table filter">
            <button
              type="button"
              className={`le-btn${filter === 'all' ? ' le-btn--primary' : ''}`}
              onClick={() => setFilter('all')}
            >
              All ({rows.length})
            </button>
            <button
              type="button"
              className={`le-btn${filter === 'attention' ? ' le-btn--primary' : ''}`}
              onClick={() => setFilter('attention')}
            >
              Attention ({attentionCount})
            </button>
            <button
              type="button"
              className={`le-btn${filter === 'dirty' ? ' le-btn--primary' : ''}`}
              onClick={() => setFilter('dirty')}
            >
              Dirty ({dirtyCount})
            </button>
            <button
              type="button"
              className={`le-btn${filter === 'evidence' ? ' le-btn--primary' : ''}`}
              onClick={() => setFilter('evidence')}
            >
              Evidence ({evidenceCount})
            </button>
          </div>
        </div>
        <p className="le-portfolio-empty">No repositories match this filter.</p>
      </section>
    )
  }

  return (
    <section className="le-portfolio-section" aria-labelledby="le-portfolio-table-h">
      <div className="le-portfolio-table-toolbar">
        <h2 id="le-portfolio-table-h" className="le-portfolio-section__title">
          Health and confidence
        </h2>
        <p className="le-portfolio-section__lead">
          Sortable view by repository. Grouping by product line or owner needs metadata not yet in workspace
          state — grouped by health below.
        </p>
        <div className="le-portfolio-filters" role="group" aria-label="Table filter">
          <button
            type="button"
            className={`le-btn${filter === 'all' ? ' le-btn--primary' : ''}`}
            onClick={() => setFilter('all')}
          >
            All ({rows.length})
          </button>
          <button
            type="button"
            className={`le-btn${filter === 'attention' ? ' le-btn--primary' : ''}`}
            onClick={() => setFilter('attention')}
          >
            Attention ({attentionCount})
          </button>
          <button
            type="button"
            className={`le-btn${filter === 'dirty' ? ' le-btn--primary' : ''}`}
            onClick={() => setFilter('dirty')}
          >
            Dirty ({dirtyCount})
          </button>
          <button
            type="button"
            className={`le-btn${filter === 'evidence' ? ' le-btn--primary' : ''}`}
            onClick={() => setFilter('evidence')}
          >
            Evidence ({evidenceCount})
          </button>
        </div>
      </div>

      <div className="le-table-wrap le-portfolio-table-wrap">
        <table className="le-table le-portfolio-table">
          <thead>
            <tr>
              <th className="le-portfolio-col-expand" aria-label="Expand" />
              {COLUMNS.map((col) => (
                <th key={col.key}>
                  <button
                    type="button"
                    className="le-portfolio-th-btn"
                    onClick={() => toggleSort(col.key)}
                  >
                    {col.label}
                    {sortKey === col.key ? (sortDir === 'asc' ? ' ▲' : ' ▼') : ''}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          {(['at_risk', 'watch', 'healthy'] as const).map((tier) => {
            const tierRows = grouped[tier]
            if (tierRows.length === 0) return null
            const tierTitle =
              tier === 'at_risk' ? 'At risk' : tier === 'watch' ? 'Watch' : 'Healthy'
            return (
              <tbody key={tier}>
                <tr className="le-portfolio-group-row">
                  <td colSpan={9} className="le-portfolio-group-label">
                    {tierTitle} ({tierRows.length})
                  </td>
                </tr>
                {tierRows.map((r) => (
                  <PortfolioRow
                    key={r.name}
                    row={r}
                    child={childByName.get(r.name)}
                    expanded={Boolean(expanded[r.name])}
                    onToggleExpand={() => toggleExpand(r.name)}
                    healthBadgeClass={healthBadgeClass}
                    healthLabel={healthLabel}
                  />
                ))}
              </tbody>
            )
          })}
        </table>
      </div>
    </section>
  )
}

function PortfolioRow({
  row,
  child,
  expanded,
  onToggleExpand,
  healthBadgeClass,
  healthLabel,
}: {
  row: RepoPortfolioRow
  child: WorkspaceChild | undefined
  expanded: boolean
  onToggleExpand: () => void
  healthBadgeClass: (h: RepoPortfolioRow['health']) => string
  healthLabel: (h: RepoPortfolioRow['health']) => string
}) {
  const name = row.name
  const enc = encodeURIComponent(name)
  const fh = row.forgeHint

  return (
    <>
      <tr className="le-portfolio-data-row">
        <td>
          <button
            type="button"
            className="le-portfolio-expand-btn"
            onClick={onToggleExpand}
            aria-expanded={expanded}
            aria-label={expanded ? 'Collapse details' : 'Expand details'}
          >
            {expanded ? '▼' : '▶'}
          </button>
        </td>
        <td className="le-name">
          <Link to={`/projects/${enc}`}>{name}</Link>
        </td>
        <td>
          <span className={healthBadgeClass(row.health)}>{healthLabel(row.health)}</span>
        </td>
        <td className="le-mono">{row.riskScore}</td>
        <td>
          {row.standardsScore != null ? (
            <>
              <span className="le-mono">{row.standardsScore}</span>
              {row.standardsTier ? <span className="le-muted"> · {row.standardsTier}</span> : null}
            </>
          ) : (
            '—'
          )}
        </td>
        <td className="le-mono">{row.roadmapCount}</td>
        <td className="le-mono">{row.wbsCount}</td>
        <td className="le-mono">
          {row.linesAdded7d != null ? row.linesAdded7d.toLocaleString() : '—'}
        </td>
        <td className="le-mono">{row.evidenceFlags}</td>
      </tr>
      {expanded && (
        <tr className="le-portfolio-detail-row">
          <td colSpan={9}>
            <div className="le-portfolio-detail">
              <p className="le-portfolio-detail__lead">Standards and readiness · decision signals</p>
              <div className="le-portfolio-detail-chips">
                {row.dirty ? (
                  <span className="le-badge le-badge--dirty">Dirty working tree</span>
                ) : (
                  <span className="le-cc-chip le-cc-chip--ok">Clean</span>
                )}
                {row.standardsTier === 'minimal' ||
                (row.standardsScore != null && row.standardsScore < 70) ? (
                  <span className="le-cc-chip le-cc-chip--warn">Standards gap</span>
                ) : (
                  <span className="le-cc-chip le-cc-chip--ok">Standards OK</span>
                )}
                {row.roadmapCount === 0 ? (
                  <span className="le-cc-chip le-cc-chip--warn">No roadmap indexed</span>
                ) : (
                  <span className="le-cc-chip le-cc-chip--ok">Roadmap</span>
                )}
                {row.wbsCount === 0 ? (
                  <span className="le-cc-chip le-cc-chip--warn">No WBS</span>
                ) : (
                  <span className="le-cc-chip le-cc-chip--ok">WBS</span>
                )}
              </div>
              {fh ? (
                <p className="le-portfolio-forge">
                  <strong>Forge artifacts:</strong>{' '}
                  {fh.has_charge ? 'charge ' : ''}
                  {fh.has_journal ? 'journal ' : ''}
                  {fh.has_versona ? 'versona ' : ''}
                  {fh.has_ember_logs ? 'ember ' : ''}
                  {!fh.has_charge && !fh.has_journal && !fh.has_versona && !fh.has_ember_logs
                    ? 'none detected'
                    : ''}
                </p>
              ) : (
                <p className="le-portfolio-forge forge-support">No forge hints for this repo.</p>
              )}
              {child?.path ? (
                <p className="forge-support">
                  <strong>Path:</strong> <code className="le-mono">{child.path}</code>
                </p>
              ) : null}
              <p className="le-portfolio-detail-links">
                <Link className="le-btn le-btn--primary" to={`/projects/${enc}`}>
                  {STUDIO_VOCAB.projectDashboard}
                </Link>{' '}
                <Link className="le-btn" to={`/projects/${enc}/charts`}>
                  {STUDIO_VOCAB.repositoryCharts}
                </Link>{' '}
                <Link className="le-btn" to={`/projects/${enc}/strategy`}>
                  {STUDIO_VOCAB.architectureStrategy}
                </Link>{' '}
                <a className="le-btn" href={`/projects/${enc}`}>
                  {FULL_WORKSPACE_UI.openFullProjectPage}
                </a>
              </p>
            </div>
          </td>
        </tr>
      )}
    </>
  )
}
