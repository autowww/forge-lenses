import type { DocsHealthFinding } from '../../api/docsHealth'
import './docs-health-project-page.css'

const DEFAULT_PAGE_SIZE = 15

type Props = {
  findings: DocsHealthFinding[]
  page: number
  pageSize?: number
  onPageChange: (page: number) => void
  categoryLabel: string
  suppressBusyId: string | null
  onOpenAsk: (f: DocsHealthFinding) => void
  onWaive: (f: DocsHealthFinding, mode: 'suppress' | 'manual') => void | Promise<void>
}

export function DocsHealthFindingsPagedBlock({
  findings,
  page,
  pageSize = DEFAULT_PAGE_SIZE,
  onPageChange,
  categoryLabel,
  suppressBusyId,
  onOpenAsk,
  onWaive,
}: Props) {
  const n = findings.length
  const totalPages = Math.max(1, Math.ceil(n / pageSize) || 1)
  const safePage = Math.min(Math.max(0, page), totalPages - 1)
  const start = safePage * pageSize
  const slice = findings.slice(start, start + pageSize)

  if (!n) {
    return (
      <section className="le-panel le-dh-findings-paged" aria-label="Findings in selected category">
        <h2 className="le-panel__title">Findings</h2>
        <p className="le-muted">No findings match the current category and filters.</p>
      </section>
    )
  }

  return (
    <section className="le-panel le-dh-findings-paged" aria-label="Findings in selected category">
      <h2 className="le-panel__title">Findings — {categoryLabel}</h2>
      <p className="forge-support" style={{ marginTop: 0 }}>
        Showing <strong>{start + 1}</strong>–<strong>{Math.min(start + slice.length, n)}</strong> of{' '}
        <strong>{n}</strong> (page {safePage + 1} of {totalPages}).
      </p>
      <ul style={{ listStyle: 'none', padding: 0, margin: '0.5rem 0 0' }}>
        {slice.map((f, i) => (
          <li
            key={f.id || `p-${start + i}-${f.title ?? ''}`}
            id={f.id ? `finding-${f.id}` : undefined}
            className="le-dh-findings-paged__item"
          >
            <strong>{f.title}</strong>
            {f.user_suppressed ? (
              <span className="le-muted" style={{ marginLeft: '0.35rem', fontSize: '0.85rem' }}>
                (waived / suppressed)
              </span>
            ) : null}
            <div className="le-muted" style={{ fontSize: '0.88rem' }}>
              {f.severity} · {f.category || '—'} · {f.fixability}
              {f.expected_score_impact != null ? ` · up to +${f.expected_score_impact} pts` : null}
            </div>
            {f.summary ? <p className="forge-support" style={{ margin: '0.35rem 0' }}>{f.summary}</p> : null}
            {f.why_it_matters ? <p className="le-muted" style={{ fontSize: '0.82rem' }}>{f.why_it_matters}</p> : null}
            {f.affected_paths?.length ? (
              <p className="le-muted" style={{ fontSize: '0.82rem' }}>
                Files: {f.affected_paths.join(', ')}
              </p>
            ) : null}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem', marginTop: '0.35rem' }}>
              <button type="button" className="le-btn le-btn--small" onClick={() => onOpenAsk(f)}>
                Open in Ask (Master-style)
              </button>
              {!f.user_suppressed && f.id ? (
                <>
                  <button
                    type="button"
                    className="le-btn le-btn--small"
                    disabled={suppressBusyId === f.id}
                    onClick={() => void onWaive(f, 'suppress')}
                  >
                    {suppressBusyId === f.id ? 'Saving…' : 'Waive / suppress'}
                  </button>
                  <button
                    type="button"
                    className="le-btn le-btn--small"
                    disabled={suppressBusyId === f.id}
                    onClick={() => void onWaive(f, 'manual')}
                  >
                    Manual follow-up
                  </button>
                </>
              ) : null}
            </div>
          </li>
        ))}
      </ul>
      {totalPages > 1 ? (
        <div className="le-dh-findings-paged__pager">
          <button
            type="button"
            className="le-btn le-btn--small"
            disabled={safePage <= 0}
            onClick={() => onPageChange(safePage - 1)}
          >
            Previous
          </button>
          <span className="le-muted forge-support">
            Page {safePage + 1} / {totalPages}
          </span>
          <button
            type="button"
            className="le-btn le-btn--small"
            disabled={safePage >= totalPages - 1}
            onClick={() => onPageChange(safePage + 1)}
          >
            Next
          </button>
        </div>
      ) : null}
    </section>
  )
}
