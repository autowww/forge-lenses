import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useWorkspace } from '../../context/WorkspaceContext'
import {
  type SitePortfolioRow,
  type SiteSortKey,
  type SortDir,
  buildSitePortfolioRows,
  formatIndexMtime,
  siteAttentionBullets,
  sortSiteRows,
} from '../../lib/sitePortfolio'
import { StatePanel } from '../page'
import { FULL_WORKSPACE_UI, STUDIO_VIEWER, STUDIO_VOCAB } from '../../nav/studioVisibleCopy'

function formatResolved(iso: string | undefined) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short',
    })
  } catch {
    return iso
  }
}

const SORT_COLS: { key: SiteSortKey; label: string }[] = [
  { key: 'name', label: 'Site' },
  { key: 'firebase_site_id', label: 'Firebase site' },
  { key: 'html_total', label: 'HTML files' },
  { key: 'coverage', label: 'Coverage' },
  { key: 'mtime', label: 'index.html mtime' },
  { key: 'roadmapCount', label: 'Roadmaps' },
]

export function SitesArtifactsHub() {
  const { state } = useWorkspace()
  const now = useMemo(() => new Date(), [])

  const rows = useMemo(() => buildSitePortfolioRows(state, now), [state, now])
  const bullets = useMemo(() => siteAttentionBullets(state, now), [state, now])

  const [sortKey, setSortKey] = useState<SiteSortKey>('name')
  const [sortDir, setSortDir] = useState<SortDir>('asc')
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})

  const sorted = useMemo(
    () => sortSiteRows(rows, sortKey, sortDir),
    [rows, sortKey, sortDir],
  )

  const summary = useMemo(() => {
    let coverageGap = 0
    let stale = 0
    let pagesIndexed = 0
    for (const r of rows) {
      if (r.coverageGap) coverageGap += 1
      if (r.staleIndex) stale += 1
      pagesIndexed += r.site.html_indexed ?? 0
    }
    return { total: rows.length, coverageGap, stale, pagesIndexed }
  }, [rows])

  function toggleSort(key: SiteSortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir(key === 'name' || key === 'firebase_site_id' ? 'asc' : 'desc')
    }
  }

  return (
    <>
      <header className="le-sites-header">
        <h1 className="le-h1">Publication and communication control center</h1>
        <p className="le-sites-header__sub">
          Site health, freshness, and planning alignment from the workspace scan — not live deploy or CI
          status. Last scan: {formatResolved(state?.resolved_at)}.
        </p>
      </header>

      <section className="le-sites-section" aria-labelledby="le-sites-summary-h">
        <h2 id="le-sites-summary-h" className="le-sites-section__title">
          Site portfolio summary
        </h2>
        <div className="le-sites-kpis">
          <div className="le-sites-kpi">
            <span className="le-sites-kpi__value">{summary.total}</span>
            <span className="le-sites-kpi__label">Firebase sites</span>
          </div>
          <div className="le-sites-kpi">
            <span className="le-sites-kpi__value le-sites-kpi__value--warn">{summary.coverageGap}</span>
            <span className="le-sites-kpi__label">
              Coverage gap (indexed {'<'} total)
            </span>
          </div>
          <div className="le-sites-kpi">
            <span className="le-sites-kpi__value le-sites-kpi__value--warn">{summary.stale}</span>
            <span className="le-sites-kpi__label">Stale / missing index mtime</span>
          </div>
          <div className="le-sites-kpi">
            <span className="le-sites-kpi__value">{summary.pagesIndexed}</span>
            <span className="le-sites-kpi__label">Pages in preview index (sum)</span>
          </div>
        </div>
      </section>

      <section className="le-sites-section" aria-labelledby="le-sites-health-h">
        <h2 id="le-sites-health-h" className="le-sites-section__title">
          Site health
        </h2>
        <p className="le-sites-section__lead">
          Freshness and ownership: index time is from <code className="le-mono">index.html</code> under the
          hosting public dir. Registry live URLs and labels stay on the full workspace UI until merged into the
          workspace API.
        </p>
        {sorted.length === 0 ? (
          <StatePanel
            variant="empty"
            density="compact"
            title="No published sites in scan"
            description="Artifacts lens needs website roots from the workspace scan. Rescan after adding Firebase or static output, or switch to Flow for the card list."
            actions={
              <Link className="le-btn le-btn--primary le-btn--small" to="/websites">
                Flow · {STUDIO_VOCAB.websites}
              </Link>
            }
          />
        ) : (
          <div className="le-table-wrap le-sites-table-wrap">
            <table className="le-table le-sites-table">
              <thead>
                <tr>
                  <th className="le-sites-col-expand" aria-label="Expand" />
                  {SORT_COLS.map((c) => (
                    <th key={c.key}>
                      <button type="button" className="le-sites-th-btn" onClick={() => toggleSort(c.key)}>
                        {c.label}
                        {sortKey === c.key ? (sortDir === 'asc' ? ' ▲' : ' ▼') : ''}
                      </button>
                    </th>
                  ))}
                  <th>Forge</th>
                  <th>Actions &amp; links</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((r) => (
                  <SiteRow
                    key={r.site.name}
                    row={r}
                    expanded={Boolean(expanded[r.site.name])}
                    onToggle={() =>
                      setExpanded((e) => ({ ...e, [r.site.name]: !e[r.site.name] }))
                    }
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="le-sites-section" aria-labelledby="le-sites-preview-h">
        <h2 id="le-sites-preview-h" className="le-sites-section__title">
          Previews awaiting action
        </h2>
        <p className="le-sites-section__lead">
          {STUDIO_VIEWER.ctaEmbeddedSitesPreview} wraps the legacy full-workspace Sites UI;{' '}
          {STUDIO_VIEWER.ctaStaticPreviewInStudio} serves /local-site files without that chrome. Deploy and CI
          status are not in scan data—use{' '}
          <a href="/websites">{FULL_WORKSPACE_UI.openFullWebsitesList}</a> when you need the root app.
        </p>
      </section>

      <section className="le-sites-section" aria-labelledby="le-sites-release-h">
        <h2 id="le-sites-release-h" className="le-sites-section__title">
          Release communication coverage
        </h2>
        <p className="le-sites-section__lead">
          Tie narrative to artifacts: <Link to="/workspace-md">{STUDIO_VOCAB.workspaceNotes}</Link>, roadmap files
          under
          each repo, and forge charge sessions. Roadmap counts in the table use repo name as{' '}
          <code className="le-mono">repo_hint</code>.
        </p>
      </section>

      <section className="le-sites-section" aria-labelledby="le-sites-risks-h">
        <h2 id="le-sites-risks-h" className="le-sites-section__title">
          Publishing risks and wins
        </h2>
        <ul className="le-sites-bullets">
          {bullets.map((b) => (
            <li key={b}>{b}</li>
          ))}
        </ul>
        <p className="forge-support">
          Cross-workspace attention: <Link to="/">Command center</Link>
        </p>
      </section>
    </>
  )
}

function SiteRow({
  row,
  expanded,
  onToggle,
}: {
  row: SitePortfolioRow
  expanded: boolean
  onToggle: () => void
}) {
  const w = row.site
  const name = w.name
  const enc = encodeURIComponent(name)
  const total = w.html_total ?? 0
  const indexed = w.html_indexed ?? 0
  const covPct = total > 0 ? Math.round((100 * indexed) / total) : null
  const fh = row.forgeHint
  const sugg = w.suggested_commands ?? {}
  const pages = Array.isArray(w.pages) ? w.pages : []
  const preview = pages.slice(0, 14)

  return (
    <>
      <tr className="le-sites-data-row">
        <td>
          <button
            type="button"
            className="le-sites-expand-btn"
            onClick={onToggle}
            aria-expanded={expanded}
            aria-label={expanded ? 'Collapse' : 'Expand'}
          >
            {expanded ? '▼' : '▶'}
          </button>
        </td>
        <td className="le-name">
          <strong>{name}</strong>
          {row.coverageGap ? (
            <span className="le-sites-badges">
              <span className="le-cc-chip le-cc-chip--warn">Coverage gap</span>
            </span>
          ) : null}
          {row.staleIndex ? (
            <span className="le-sites-badges">
              <span className="le-badge le-badge--dirty">Stale index</span>
            </span>
          ) : null}
        </td>
        <td className="le-mono">{w.firebase_site_id?.trim() || '—'}</td>
        <td className="le-mono">{total}</td>
        <td className="le-mono">
          {indexed} / {total}
          {covPct != null ? <span className="le-muted"> ({covPct}%)</span> : null}
        </td>
        <td className="le-mono">{formatIndexMtime(w.index_html_mtime ?? undefined)}</td>
        <td className="le-mono">
          {row.roadmapCount}
          {row.wbsCount > 0 ? (
            <span className="le-muted"> · WBS {row.wbsCount}</span>
          ) : null}
        </td>
        <td>
          {fh ? (
            <span className="le-sites-forge-chips">
              {fh.has_charge ? 'charge ' : ''}
              {fh.has_journal ? 'journal ' : ''}
              {fh.has_versona ? 'versona ' : ''}
              {fh.has_ember_logs ? 'ember' : ''}
              {!fh.has_charge && !fh.has_journal && !fh.has_versona && !fh.has_ember_logs ? '—' : ''}
            </span>
          ) : (
            '—'
          )}
        </td>
        <td className="le-sites-actions-cell">
          <div className="le-sites-cmd">
            {sugg.deploy ? (
              <p className="le-sites-cmd-line">
                <span className="le-sites-cmd-label">deploy</span>{' '}
                <code className="le-sites-cmd-code">{sugg.deploy}</code>
              </p>
            ) : null}
            {sugg.build ? (
              <p className="le-sites-cmd-line">
                <span className="le-sites-cmd-label">build</span>{' '}
                <code className="le-sites-cmd-code">{sugg.build}</code>
              </p>
            ) : null}
          </div>
          <div className="le-sites-links">
            <Link className="le-sites-link-secondary" to={`/websites/browse/${enc}`}>
              {STUDIO_VIEWER.ctaStaticPreviewInStudio}
            </Link>
          </div>
        </td>
      </tr>
      {expanded && (
        <tr className="le-sites-detail-row">
          <td colSpan={9}>
            <div className="le-sites-detail">
              <p>
                <strong>Hosting public:</strong> <code className="le-mono">{w.hosting_public ?? '—'}</code>
              </p>
              {row.child?.path ? (
                <p>
                  <strong>Repo path:</strong> <code className="le-mono">{row.child.path}</code>
                </p>
              ) : null}
              <h4 className="le-sites-detail__subtitle">Preview pages (first {preview.length})</h4>
              {preview.length === 0 ? (
                <StatePanel
                  variant="empty"
                  density="compact"
                  title="No indexed pages"
                  description="The preview index may be empty for this site, or the scan has not indexed HTML paths yet."
                />
              ) : (
                <ul className="le-sites-page-list">
                  {preview.map((p, i) => (
                    <li key={i}>
                      <span className="le-mono">{p.path ?? '—'}</span>
                      {p.label ? <span className="le-muted"> — {p.label}</span> : null}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  )
}
