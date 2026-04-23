import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { getDocsHealthWorkItems, postProjectDocsHealth, type DocsHealthLiveSessionRow } from '../../api/docsHealth'
import { useDocsHealthLive } from '../../context/DocsHealthLiveContext'
import { STUDIO_VOCAB } from '../../nav/studioVisibleCopy'

type Row = {
  id?: string
  title?: string
  project?: string
  status?: string
  severity?: string
  kind?: string
  finding_id?: string
  project_docs_health_href?: string
  project_docs_health_master_href?: string
  docs_health_session_href?: string
  workspace_md_href?: string
  expected_score_impact?: number
  tasklet_run_state?: string
}

export function DocsHealthWorkBand() {
  const dhLive = useDocsHealthLive()
  const [rows, setRows] = useState<Row[]>([])
  const [busy, setBusy] = useState<string | null>(null)

  const liveByProject = useMemo(() => {
    const m = new Map<string, DocsHealthLiveSessionRow>()
    for (const s of dhLive?.globalSessions ?? []) {
      const p = String(s.project || '').trim()
      if (p && !m.has(p)) m.set(p, s)
    }
    return m
  }, [dhLive?.globalSessions])

  const load = useCallback(() => {
    void getDocsHealthWorkItems()
      .then((d) => setRows((d.work_items ?? []) as Row[]))
      .catch(() => setRows([]))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const complete = async (id: string, project: string) => {
    setBusy(id)
    try {
      await postProjectDocsHealth(project, { op: 'work_complete', work_item_id: id })
      load()
    } finally {
      setBusy(null)
    }
  }

  if (!rows.length) return null

  return (
    <section className="le-panel" aria-label="Documentation follow-ups">
      <h2 className="le-panel__title">Documentation follow-ups</h2>
      <p className="forge-support">
        Open scan debt items and active <strong>tasklet</strong> remediation runs that need input, approval, resume, or
        review. Resolve tasklet rows in the session (not via Mark done).
      </p>
      <ul className="le-plan-section__list" style={{ listStyle: 'none', padding: 0, marginTop: '0.75rem' }}>
        {rows.map((r) => {
          const proj = r.project ?? ''
          const enc = encodeURIComponent(proj)
          const href = r.project_docs_health_href ?? `/projects/${enc}/docs-health`
          const hash = r.finding_id ? `#finding-${encodeURIComponent(r.finding_id)}` : ''
          const live = proj ? liveByProject.get(proj) : undefined
          const liveHref =
            live?.session_id && proj
              ? `/projects/${encodeURIComponent(proj)}/docs-health/session/${encodeURIComponent(String(live.session_id))}`
              : null
          return (
            <li
              key={r.id}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                justifyContent: 'space-between',
                gap: '0.75rem',
                padding: '0.5rem 0',
                borderBottom: '1px solid var(--le-border-muted, #e5e5e5)',
              }}
            >
              <div>
                <div style={{ fontWeight: 600 }}>{r.title || 'Follow-up'}</div>
                <div className="le-muted" style={{ fontSize: '0.9rem' }}>
                  {r.kind === 'tasklet_run' && r.tasklet_run_state ? (
                    <span>tasklet · {r.tasklet_run_state}</span>
                  ) : (
                    <>
                      {r.severity ? <span>{r.severity}</span> : null}
                      {r.severity && r.expected_score_impact != null ? ' · ' : null}
                      {r.expected_score_impact != null ? `up to +${r.expected_score_impact} pts` : null}
                    </>
                  )}
                </div>
                <div className="le-muted" style={{ fontSize: '0.9rem', marginTop: '0.15rem' }}>
                  <Link to={`${href}${hash}`}>
                    {proj ? `${proj} · ` : ''}
                    {STUDIO_VOCAB.docsHealth}
                    {r.finding_id ? ` · finding ${r.finding_id}` : ''}
                  </Link>
                  {liveHref ? (
                    <>
                      {' '}
                      ·{' '}
                      <Link to={liveHref}>Live session</Link>
                    </>
                  ) : null}
                  {r.docs_health_session_href ? (
                    <>
                      {' '}
                      ·{' '}
                      <Link to={r.docs_health_session_href}>Session</Link>
                    </>
                  ) : null}
                  {r.project_docs_health_master_href ? (
                    <>
                      {' '}
                      ·{' '}
                      <Link to={r.project_docs_health_master_href}>Master</Link>
                    </>
                  ) : null}
                  {r.workspace_md_href ? (
                    <>
                      {' '}
                      ·{' '}
                      <Link to={r.workspace_md_href}>Evidence</Link>
                    </>
                  ) : null}
                </div>
              </div>
              {r.id && proj && r.kind !== 'tasklet_run' ? (
                <button
                  type="button"
                  className="le-btn le-btn--small"
                  disabled={busy === r.id}
                  onClick={() => void complete(r.id!, proj)}
                >
                  Mark done
                </button>
              ) : null}
            </li>
          )
        })}
      </ul>
    </section>
  )
}
