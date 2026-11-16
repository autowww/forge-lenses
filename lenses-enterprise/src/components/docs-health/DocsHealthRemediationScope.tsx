import type { DocsHealthRemediationScope as Scope } from '../../api/docsHealth'
import { TechnicalDetails } from '../page'

type Props = {
  scope: Scope | undefined
}

export function DocsHealthRemediationScopePanel({ scope }: Props) {
  if (!scope) return null

  const n = scope.finding_count ?? 0
  const rules = scope.rules_breakdown_list?.length
    ? scope.rules_breakdown_list
    : Object.entries(scope.rules_breakdown || {}).map(([rule_code, count]) => ({ rule_code, count }))

  return (
    <section className="le-panel le-dh-scope" aria-label="Remediation scope and gaps" style={{ marginTop: '1rem' }}>
      <h2 className="le-panel__title">What this run is fixing</h2>
      <p className="forge-support le-dh-scope__lead">{scope.agent_intent}</p>
      {scope.note ? (
        <p className="le-muted le-dh-scope__note" style={{ fontSize: '0.9rem', maxWidth: '52rem' }}>
          {scope.note}
        </p>
      ) : null}

      <div className="le-dh-scope__stats">
        <div className="le-dh-scope__stat">
          <span className="le-dh-scope__stat-value">{n}</span>
          <span className="le-dh-scope__stat-label">
            documentation gap{n === 1 ? '' : 's'} in this cluster
          </span>
        </div>
        {scope.distinct_path_count != null && scope.distinct_path_count > 0 ? (
          <div className="le-dh-scope__stat">
            <span className="le-dh-scope__stat-value">{scope.distinct_path_count}</span>
            <span className="le-dh-scope__stat-label">distinct paths touched by findings</span>
          </div>
        ) : null}
      </div>

      {rules.length > 0 ? (
        <>
          <h3 className="le-dh-scope__subhead">Gaps by rule</h3>
          <p className="le-muted" style={{ fontSize: '0.88rem', maxWidth: '48rem', marginTop: '0.15rem' }}>
            Rule codes group the same kind of documentation issue (e.g. links, traceability, diagrams).
          </p>
          <ul className="le-dh-scope__rules">
            {rules.map((r) => (
              <li key={r.rule_code}>
                <code>{r.rule_code}</code>
                <span className="le-dh-scope__rule-count">{r.count}</span>
              </li>
            ))}
          </ul>
        </>
      ) : null}

      {scope.sample_findings && scope.sample_findings.length > 0 ? (
        <>
          <h3 className="le-dh-scope__subhead">Examples</h3>
          <table className="le-dh-scope__table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Rule</th>
                <th>Paths</th>
              </tr>
            </thead>
            <tbody>
              {scope.sample_findings.map((f) => (
                <tr key={f.id || f.title}>
                  <td>
                    <span className="le-dh-scope__finding-title">{f.title || '—'}</span>
                    {f.summary ? (
                      <div className="le-dh-scope__finding-summary le-muted" style={{ fontSize: '0.82rem' }}>
                        {f.summary}
                      </div>
                    ) : null}
                  </td>
                  <td>
                    <code>{f.rule_code}</code>
                    {f.severity ? <span className="le-dh-scope__sev">{f.severity}</span> : null}
                  </td>
                  <td className="le-dh-scope__paths">
                    {(f.affected_paths || []).slice(0, 3).map((p) => (
                      <div key={p}>
                        <code>{p}</code>
                      </div>
                    ))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      ) : null}

      {scope.repo_md_context?.hits && scope.repo_md_context.hits.length > 0 ? (
        <>
          <h3 className="le-dh-scope__subhead">Repository Markdown (relevant to this finding set)</h3>
          <p className="le-muted" style={{ fontSize: '0.88rem', maxWidth: '52rem' }}>
            Search of <code>.md</code> files in this project folder — keywords from findings and rule codes, plus paths
            from the scan. Use these guardrails before accepting agent text.
            {scope.repo_md_context.scanned_file_count != null ? (
              <>
                {' '}
                Scanned up to <strong>{scope.repo_md_context.scanned_file_count}</strong> candidate file(s).
              </>
            ) : null}
          </p>
          {scope.repo_md_context.query_terms && scope.repo_md_context.query_terms.length > 0 ? (
            <TechnicalDetails summary="Query terms used" defaultOpen={false}>
              <p className="forge-support" style={{ fontSize: '0.82rem' }}>
                {scope.repo_md_context.query_terms.join(', ')}
              </p>
            </TechnicalDetails>
          ) : null}
          <div className="le-dh-scope__repo-md-list">
            {scope.repo_md_context.hits.map((h) => (
              <article key={h.path} className="le-dh-scope__repo-md-card">
                <div className="le-dh-scope__repo-md-head">
                  <code className="le-dh-scope__repo-md-path">{h.path}</code>
                  {h.source === 'affected_path' ? (
                    <span className="le-dh-scope__repo-md-badge">affected path</span>
                  ) : null}
                  {typeof h.relevance_score === 'number' ? (
                    <span className="le-muted" style={{ fontSize: '0.75rem' }}>
                      score {h.relevance_score}
                    </span>
                  ) : null}
                </div>
                {h.match_terms && h.match_terms.length > 0 ? (
                  <p className="le-muted" style={{ fontSize: '0.72rem', margin: '0.2rem 0 0' }}>
                    Matches: {h.match_terms.slice(0, 10).join(', ')}
                  </p>
                ) : null}
                <pre className="le-preview le-dh-scope__pre le-dh-scope__repo-md-excerpt">{h.excerpt || '—'}</pre>
              </article>
            ))}
          </div>
        </>
      ) : null}

      {scope.distinct_affected_paths && scope.distinct_affected_paths.length > 0 ? (
        <TechnicalDetails summary="All affected paths (sample)" defaultOpen={false}>
          <ul className="le-dh-scope__path-list">
            {scope.distinct_affected_paths.map((p) => (
              <li key={p}>
                <code>{p}</code>
              </li>
            ))}
          </ul>
        </TechnicalDetails>
      ) : null}

      {scope.before_after ? (
        <>
          <h3 className="le-dh-scope__subhead">Before / after (excerpts)</h3>
          <p className="le-muted" style={{ fontSize: '0.88rem' }}>
            Path: <code>{scope.before_after.path}</code>
          </p>
          <div className="le-dh-scope__split">
            <div>
              <div className="le-dh-scope__split-label">Before (repo)</div>
              <pre className="le-preview le-dh-scope__pre">{scope.before_after.before_excerpt || '—'}</pre>
            </div>
            <div>
              <div className="le-dh-scope__split-label">After (proposed)</div>
              <pre className="le-preview le-dh-scope__pre">{scope.before_after.after_excerpt || '—'}</pre>
            </div>
          </div>
        </>
      ) : null}

      {scope.unified_diff_excerpt ? (
        <>
          <h3 className="le-dh-scope__subhead">Unified diff preview</h3>
          <pre className="le-preview le-dh-scope__pre le-dh-scope__diff">{scope.unified_diff_excerpt}</pre>
        </>
      ) : null}
    </section>
  )
}
