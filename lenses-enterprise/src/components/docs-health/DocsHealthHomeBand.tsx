import { useId } from 'react'
import { Link } from 'react-router-dom'
import { STUDIO_VOCAB } from '../../nav/studioVisibleCopy'
import { useDocsHealthSummary } from '../../context/DocsHealthSummaryContext'

export function DocsHealthHomeBand() {
  const hId = useId()
  const rollupId = useId()
  const { data } = useDocsHealthSummary()

  if (!data?.ok || !data.projects?.length) return null

  const attention = data.projects.filter((p) => p.needs_attention)
  const withChecklist = data.projects_with_contract_file ?? 0
  const withList = data.projects_with_inventory ?? 0
  const rollup = data.rollup
  const avg = rollup?.average_last_score
  const critProjects = rollup?.projects_with_critical_open_findings ?? 0
  const awaiting = rollup?.open_docs_work_items_total ?? 0
  const taskletFollow = rollup?.open_tasklet_followups_total ?? 0
  const tokensFlight = rollup?.estimated_llm_tokens_in_flight ?? 0
  const scoreGains = rollup?.projects_with_recent_score_gain ?? 0
  const live = data.live_docs_health_sessions ?? []

  return (
    <section className="le-panel" aria-labelledby={hId}>
      <h2 id={hId} className="le-panel__title">
        Documentation health
      </h2>
      <p className="forge-support">
        {STUDIO_VOCAB.docsHealth} is available for your repositories. {withChecklist} project(s) use a team checklist
        file, and {withList} already have a recent documentation file list.
      </p>
      <div
        className="le-muted"
        id={rollupId}
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(10rem, 1fr))',
          gap: '0.75rem',
          marginTop: '0.75rem',
        }}
        role="group"
        aria-label="Documentation health rollup"
      >
        <div>
          <div style={{ fontSize: '0.85rem' }}>Average last score</div>
          <div style={{ fontSize: '1.35rem', fontWeight: 700 }}>{avg != null ? `${avg}/100` : '—'}</div>
        </div>
        <div>
          <div style={{ fontSize: '0.85rem' }}>Projects with critical findings</div>
          <div style={{ fontSize: '1.35rem', fontWeight: 700 }}>{critProjects}</div>
        </div>
        <div>
          <div style={{ fontSize: '0.85rem' }}>Follow-ups awaiting action</div>
          <div style={{ fontSize: '1.35rem', fontWeight: 700 }}>{awaiting}</div>
        </div>
        <div>
          <div style={{ fontSize: '0.85rem' }}>Tasklet runs needing attention</div>
          <div style={{ fontSize: '1.35rem', fontWeight: 700 }}>{taskletFollow}</div>
        </div>
        <div>
          <div style={{ fontSize: '0.85rem' }}>LLM tokens (live sessions)</div>
          <div style={{ fontSize: '1.35rem', fontWeight: 700 }}>{tokensFlight > 0 ? tokensFlight.toLocaleString() : '—'}</div>
        </div>
        <div>
          <div style={{ fontSize: '0.85rem' }}>Projects with recent score gain</div>
          <div style={{ fontSize: '1.35rem', fontWeight: 700 }}>{scoreGains}</div>
        </div>
      </div>
      {attention.length > 0 ? (
        <p className="forge-support" role="status" style={{ marginTop: '0.75rem' }}>
          {attention.length} project(s) may need attention — open one to review or update the documentation list.
        </p>
      ) : (
        <p className="forge-support" role="status" style={{ marginTop: '0.75rem' }}>
          No urgent documentation signals from the last quality run.
        </p>
      )}
      <ul className="le-muted" style={{ marginTop: '0.5rem', paddingLeft: '1.25rem' }}>
        {attention.slice(0, 5).map((p) => (
          <li key={p.project}>
            <Link to={`/projects/${encodeURIComponent(p.project)}/docs-health`}>{p.project}</Link>
            {p.last_score != null ? ` — last score ${p.last_score}/100` : null}
            {typeof p.last_score_delta === 'number' && p.last_score_delta !== 0 ? (
              <span>
                {' '}
                (last delta {p.last_score_delta > 0 ? '+' : ''}
                {p.last_score_delta})
              </span>
            ) : null}
            {typeof p.critical_open_findings === 'number' && p.critical_open_findings > 0
              ? ` · ${p.critical_open_findings} critical`
              : null}
          </li>
        ))}
      </ul>
      {live.length > 0 ? (
        <div style={{ marginTop: '0.75rem' }}>
          <h3 className="le-panel__title" style={{ fontSize: '1rem' }}>
            Active docs sessions
          </h3>
          <ul className="le-muted" style={{ paddingLeft: '1.25rem' }}>
            {live.slice(0, 6).map((s) => (
              <li key={`${s.project}-${s.session_id}`}>
                <Link to={`/projects/${encodeURIComponent(String(s.project))}/docs-health/session/${encodeURIComponent(String(s.session_id))}`}>
                  {s.project}
                </Link>
                {s.cluster_label ? ` · ${s.cluster_label}` : null}
                {typeof s.total_tokens === 'number' && s.total_tokens > 0 ? ` · ${s.total_tokens.toLocaleString()} tok` : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  )
}
