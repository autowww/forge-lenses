import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import type { WorkspaceMdIndexEntry } from '../../api/workspaceMdIndex'
import { EVIDENCE_IA, STUDIO_VOCAB } from '../../nav/studioVisibleCopy'

const CATEGORY_ORDER = ['charge', 'journal', 'ember', 'forge_logs'] as const

const CATEGORY_LABEL: Record<string, string> = {
  charge: 'Charge',
  journal: 'Journal',
  ember: 'Ember',
  forge_logs: 'Forge logs',
}

const CATEGORY_BLURB: Record<string, string> = {
  charge: 'Operational tables — often tied to Today and delivery.',
  journal: 'Dated notes and ADRs under forge/journal/.',
  ember: 'Session transcripts under ember-logs/.',
  forge_logs: 'Work logs and linked markdown under forge-logs/.',
}

function workspaceMdHref(path: string, contextProject: string): string {
  const q = new URLSearchParams()
  q.set('p', path)
  if (contextProject.trim()) q.set('contextProject', contextProject.trim())
  return `/workspace-md?${q.toString()}`
}

type Props = {
  contextProject: string
  files: WorkspaceMdIndexEntry[]
  indexLoading: boolean
  indexError: string | null
  indexTruncated: boolean
  pinned: string[]
  recent: string[]
  onTogglePin: (path: string) => void
  onClearRecent: () => void
}

export function WorkspaceMdHub({
  contextProject,
  files,
  indexLoading,
  indexError,
  indexTruncated,
  pinned,
  recent,
  onTogglePin,
  onClearRecent,
}: Props) {
  const [filter, setFilter] = useState('')

  const byCategory = useMemo(() => {
    const m = new Map<string, WorkspaceMdIndexEntry[]>()
    const q = filter.trim().toLowerCase()
    for (const e of files) {
      if (q && !e.rel_path.toLowerCase().includes(q)) continue
      const list = m.get(e.category) ?? []
      list.push(e)
      m.set(e.category, list)
    }
    return m
  }, [files, filter])

  return (
    <div className="le-ws-md-hub">
      <section className="le-ws-md-hub__section" aria-labelledby="ws-md-ia-heading">
        <h2 id="ws-md-ia-heading" className="le-ws-md-hub__h">
          {EVIDENCE_IA.hubCompareHeading}
        </h2>
        <div className="le-ws-md-hub__compare">
          <div className="le-ws-md-hub__compare-card">
            <h3 className="le-ws-md-hub__compare-title">
              <span className="le-content-type-badge le-content-type-badge--evidence">Evidence</span>{' '}
              {STUDIO_VOCAB.workspaceNotes}
            </h3>
            <p className="le-ws-md-hub__compare-body">{EVIDENCE_IA.evidenceDefinition}</p>
          </div>
          <div className="le-ws-md-hub__compare-card">
            <h3 className="le-ws-md-hub__compare-title">
              <span className="le-content-type-badge le-content-type-badge--docs">Docs</span> {STUDIO_VOCAB.tutorials}{' '}
              &amp; reference
            </h3>
            <p className="le-ws-md-hub__compare-body">{EVIDENCE_IA.docsDefinition}</p>
            <Link className="le-ws-md-hub__compare-link" to="/tutorials">
              Open {STUDIO_VOCAB.tutorials}
            </Link>
          </div>
          <div className="le-ws-md-hub__compare-card">
            <h3 className="le-ws-md-hub__compare-title">
              <span className="le-content-type-badge le-content-type-badge--decisions">Decisions</span> Methodology
              graph
            </h3>
            <p className="le-ws-md-hub__compare-body">{EVIDENCE_IA.decisionsDefinition}</p>
            <Link className="le-ws-md-hub__compare-link" to="/knowledge/methodology/decisions">
              Open decision registry
            </Link>
          </div>
        </div>
      </section>

      <section className="le-ws-md-hub__section" aria-labelledby="ws-md-recents-heading">
        <h2 id="ws-md-recents-heading" className="le-ws-md-hub__h">
          Pinned &amp; recent
        </h2>
        <p className="le-ws-md-hub__lead">
          Pick up where you left off — pin files while browsing the index below. Deep links from Plan and project pages
          land here with the same scope.
        </p>
        {pinned.length > 0 ? (
          <div className="le-ws-md-hub__subblock">
            <h3 className="le-ws-md-hub__subh">Pinned</h3>
            <ul className="le-ws-md-hub__link-rows">
              {pinned.map((path) => (
                <li key={`pin-${path}`} className="le-ws-md-hub__link-row">
                  <Link className="le-ws-md-hub__path-link" to={workspaceMdHref(path, contextProject)}>
                    <span className="le-ws-md-hub__file-title">{path.split('/').pop()}</span>
                    <span className="le-ws-md-hub__file-path" title={path}>
                      {path}
                    </span>
                  </Link>
                  <button
                    type="button"
                    className="le-ws-md-hub__pin"
                    aria-label={`Unpin ${path}`}
                    onClick={() => onTogglePin(path)}
                  >
                    Unpin
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <p className="le-ws-md-hub__muted">No pins yet — use Pin while viewing a file or from the browse list.</p>
        )}
        {recent.length > 0 ? (
          <div className="le-ws-md-hub__subblock">
            <div className="le-ws-md-hub__subhead-row">
              <h3 className="le-ws-md-hub__subh">Recently opened</h3>
              <button type="button" className="le-ws-md-hub__text-btn" onClick={onClearRecent}>
                Clear list
              </button>
            </div>
            <ul className="le-ws-md-hub__link-rows">
              {recent.map((path) => (
                <li key={`rec-${path}`} className="le-ws-md-hub__link-row">
                  <Link className="le-ws-md-hub__path-link" to={workspaceMdHref(path, contextProject)}>
                    <span className="le-ws-md-hub__file-title">{path.split('/').pop()}</span>
                    <span className="le-ws-md-hub__file-path" title={path}>
                      {path}
                    </span>
                  </Link>
                  <button
                    type="button"
                    className="le-ws-md-hub__pin"
                    aria-label={pinned.includes(path) ? `Unpin ${path}` : `Pin ${path}`}
                    onClick={() => onTogglePin(path)}
                  >
                    {pinned.includes(path) ? 'Unpin' : 'Pin'}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <p className="le-ws-md-hub__muted">No recent files yet — open an item from the index.</p>
        )}
      </section>

      <section className="le-ws-md-hub__section" aria-labelledby="ws-md-browser-heading">
        <h2 id="ws-md-browser-heading" className="le-ws-md-hub__h">
          {EVIDENCE_IA.hubBrowseHeading}
        </h2>
        <p className="le-ws-md-hub__lead">{EVIDENCE_IA.hubBrowseLead}</p>
        <label className="le-ws-md-hub__filter-label">
          <span className="le-ws-md-hub__filter-text">Filter indexed paths</span>
          <input
            className="le-input le-ws-md-hub__filter-input"
            type="search"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="Substring match"
            autoComplete="off"
          />
        </label>
        {indexLoading ? (
          <p className="le-ws-md-hub__muted">Scanning workspace for evidence files…</p>
        ) : indexError ? (
          <p className="le-ws-md-hub__warn" role="status">
            {indexError} You can still open files from Plan or project links, or use advanced path entry at the
            bottom of the page.
          </p>
        ) : files.length === 0 ? (
          <p className="le-ws-md-hub__warn" role="status">
            No allowlisted markdown in this scan. Typical evidence includes <code>forge/charge.md</code>, files under{' '}
            <code>forge/journal/</code>, <code>ember-logs/</code>, and <code>forge-logs/**/*.md</code>. Rescan the
            workspace after adding files.
          </p>
        ) : (
          <>
            {indexTruncated ? (
              <p className="le-ws-md-hub__warn" role="status">
                List capped at 500 files — narrow with the filter.
              </p>
            ) : null}
            <div className="le-ws-md-hub__groups">
              {CATEGORY_ORDER.map((cat) => {
                const group = byCategory.get(cat)
                if (!group?.length) return null
                return (
                  <details key={cat} className="le-ws-md-hub__details" open>
                    <summary className="le-ws-md-hub__summary">
                      {CATEGORY_LABEL[cat] ?? cat}
                      <span className="le-ws-md-hub__count">{group.length}</span>
                    </summary>
                    <p className="le-ws-md-hub__cat-blurb">{CATEGORY_BLURB[cat] ?? ''}</p>
                    <ul className="le-ws-md-hub__link-rows">
                      {group.map((e) => (
                        <li key={e.rel_path} className="le-ws-md-hub__link-row">
                          <Link className="le-ws-md-hub__path-link" to={workspaceMdHref(e.rel_path, contextProject)}>
                            <span className="le-ws-md-hub__title-line">
                              <span
                                className={`le-content-type-badge le-ws-md-hub__row-badge le-content-type-badge--${cat === 'charge' ? 'evidence' : cat === 'journal' ? 'docs' : 'graph'}`}
                              >
                                {CATEGORY_LABEL[e.category] ?? e.category}
                              </span>
                              <span className="le-ws-md-hub__file-title">{e.rel_path.split('/').pop()}</span>
                            </span>
                            <span className="le-ws-md-hub__file-path" title={e.rel_path}>
                              {e.rel_path}
                            </span>
                          </Link>
                          <button
                            type="button"
                            className="le-ws-md-hub__pin"
                            aria-label={pinned.includes(e.rel_path) ? `Unpin ${e.rel_path}` : `Pin ${e.rel_path}`}
                            onClick={() => onTogglePin(e.rel_path)}
                          >
                            {pinned.includes(e.rel_path) ? 'Unpin' : 'Pin'}
                          </button>
                        </li>
                      ))}
                    </ul>
                  </details>
                )
              })}
            </div>
          </>
        )}
      </section>
    </div>
  )
}
