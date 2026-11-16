import { Link } from 'react-router-dom'
import { MarkdownBody } from '../MarkdownBody'
import { storyDefinitionMarkdown, storySlotCellToMarkdown } from '../../util/storyHubSlots'

type TaskRow = { id?: string; title?: string }

function tasksFromDefinition(story: Record<string, unknown>): TaskRow[] {
  const def = story.definition as { kind?: string; tasks?: TaskRow[] } | undefined
  if (!def || def.kind !== 'story' || !Array.isArray(def.tasks)) return []
  return def.tasks.filter((t) => t && (t.id || t.title))
}

function entityList(
  label: string,
  rows: { entity_id?: string; display_name?: unknown; external_ref?: unknown }[],
) {
  if (!rows.length) return null
  return (
    <div style={{ marginTop: '0.5rem' }}>
      <strong>{label}</strong>
      <ul className="le-list" style={{ margin: '0.25rem 0', paddingLeft: '1.1rem' }}>
        {rows.map((row) => (
          <li key={row.entity_id ?? String(row.display_name)}>
            <code className="le-mono">{row.entity_id ?? '—'}</code>
            {row.display_name ? <> · {String(row.display_name)}</> : null}
            {row.external_ref ? (
              <>
                {' '}
                <span className="forge-support">({String(row.external_ref)})</span>
              </>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  )
}

export function StoryHubPanel({ story, nodeId }: { story: Record<string, unknown>; nodeId: string }) {
  const ce = story.code_execution as Record<string, unknown> | undefined
  const graph = ce?.graph as Record<string, unknown> | undefined
  const repoCx = ce?.repo as Record<string, unknown> | undefined
  const cicd = ce?.cicd_trace as Record<string, unknown> | undefined
  const qtrace = ce?.quality_trace as Record<string, unknown> | undefined
  const qevidence = ce?.quality_evidence as Record<string, unknown> | undefined
  const strace = ce?.security_trace as Record<string, unknown> | undefined
  const sevidence = ce?.devsecops_evidence as Record<string, unknown> | undefined
  const otrace = ce?.ops_trace as Record<string, unknown> | undefined
  const oevidence = ce?.ops_delivery_evidence as Record<string, unknown> | undefined
  const sv = story.story_view as Record<string, unknown> | undefined
  const defText = storyDefinitionMarkdown(story, sv)
  const slots = sv?.slots as Record<string, unknown> | undefined
  const slotEntries =
    slots && typeof slots === 'object'
      ? Object.entries(slots).filter(([, v]) => storySlotCellToMarkdown(v).trim().length > 0)
      : []
  const tasks = tasksFromDefinition(story)
  const title =
    (story.definition as { title?: string } | undefined)?.title ||
    (sv?.story_id as string | undefined) ||
    nodeId

  return (
    <div className="le-story-hub-panel">
      <header className="le-story-hub-panel__head">
        <p className="le-story-hub-panel__eyebrow">Story</p>
        <h2 className="le-story-hub-panel__title">{title}</h2>
        <p className="le-story-hub-panel__id">
          <span className="le-muted">ID</span> <code className="le-mono">{nodeId}</code>
        </p>
      </header>

      {(() => {
        const ol = story.outcome_loop as { outcome_launches?: unknown[] } | undefined
        const launches = Array.isArray(ol?.outcome_launches) ? ol!.outcome_launches! : []
        if (!launches.length) return null
        return (
          <section className="le-story-hub-panel__block" aria-labelledby="le-sh-outcome">
            <h3 id="le-sh-outcome" className="le-story-hub-panel__h">
              Outcomes / PDLC loop (orchestration)
            </h3>
            <ul className="le-story-hub-panel__task-list" style={{ listStyle: 'disc', paddingLeft: '1.2rem' }}>
              {launches.map((raw) => {
                const row = raw as {
                  launch_id?: string
                  release_id?: string
                  signal_count?: number
                  demand_signal_ids?: string[]
                  scores?: { launch_confidence?: number; explanations?: string[] }
                }
                const ex = row.scores?.explanations?.[0]
                return (
                  <li key={row.launch_id ?? 'ol'} style={{ marginBottom: '0.5rem' }}>
                    <code className="le-mono">{row.launch_id}</code> · release{' '}
                    <code>{row.release_id ?? '—'}</code> · {row.signal_count ?? 0} signals · confidence{' '}
                    <strong>{row.scores?.launch_confidence ?? '—'}</strong>
                    {row.demand_signal_ids?.length ? (
                      <span className="forge-support">
                        {' '}
                        · demand <code>{row.demand_signal_ids[0]}</code>
                      </span>
                    ) : null}
                    {ex ? <div className="forge-support">{ex}</div> : null}
                  </li>
                )
              })}
            </ul>
          </section>
        )
      })()}

      {(() => {
        const hl = story.handoff_loop as { handoff_packages?: unknown[] } | undefined
        const pkgs = Array.isArray(hl?.handoff_packages) ? hl!.handoff_packages! : []
        if (!pkgs.length) return null
        return (
          <section className="le-story-hub-panel__block" aria-labelledby="le-sh-handoff">
            <h3 id="le-sh-handoff" className="le-story-hub-panel__h">
              Handoff / return (orchestration)
            </h3>
            <ul className="le-story-hub-panel__task-list" style={{ listStyle: 'disc', paddingLeft: '1.2rem' }}>
              {pkgs.map((raw) => {
                const row = raw as {
                  package_id?: string
                  status?: Record<string, unknown>
                  gaps?: Record<string, unknown>
                }
                const st = row.status ?? {}
                const gp = row.gaps ?? {}
                const missA = Array.isArray(gp.missing_acceptance) ? (gp.missing_acceptance as string[]) : []
                const missE = Array.isArray(gp.missing_evidence) ? (gp.missing_evidence as string[]) : []
                return (
                  <li key={row.package_id ?? 'pkg'} style={{ marginBottom: '0.5rem' }}>
                    <code className="le-mono">{row.package_id}</code> · target{' '}
                    <strong>{String(st.target_key ?? '—')}</strong> · LP{' '}
                    <code>{String(st.launch_pack_version ?? '—')}</code>
                    {missA.length > 0 ? (
                      <span className="forge-support">
                        {' '}
                        — missing acceptance: {missA.join(', ')}
                      </span>
                    ) : null}
                    {missE.length > 0 ? (
                      <span className="forge-support">
                        {' '}
                        — missing evidence: {missE.join(', ')}
                      </span>
                    ) : null}
                  </li>
                )
              })}
            </ul>
          </section>
        )
      })()}

      {tasks.length > 0 && (
        <section className="le-story-hub-panel__block" aria-labelledby="le-sh-tasks">
          <h3 id="le-sh-tasks" className="le-story-hub-panel__h">
            Tasks ({tasks.length})
          </h3>
          <ul className="le-story-hub-panel__task-list">
            {tasks.map((t) => (
              <li key={t.id || t.title}>
                {t.id ? <code className="le-mono">{t.id}</code> : null}
                {t.id && t.title ? ' · ' : null}
                <span>{t.title ?? '—'}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {defText && (
        <section className="le-story-hub-panel__block" aria-labelledby="le-sh-def">
          <h3 id="le-sh-def" className="le-story-hub-panel__h">
            Definition
          </h3>
          <MarkdownBody text={defText} />
        </section>
      )}

      {ce && (graph?.linked || repoCx) ? (
        <section className="le-story-hub-panel__block" aria-labelledby="le-sh-code">
          <h3 id="le-sh-code" className="le-story-hub-panel__h">
            Code &amp; merge readiness
          </h3>
          {graph?.linked ? (
            <div className="forge-support" style={{ marginBottom: '0.75rem' }}>
              <p style={{ marginTop: 0 }}>
                <strong>Graph:</strong> merge readiness{' '}
                <code className="le-mono">{String(graph.merge_readiness ?? '—')}</code>
              </p>
              {(graph.change_requests as { display_name?: string; url?: string | null; number?: number }[])?.length ? (
                <ul className="le-list" style={{ margin: '0.25rem 0', paddingLeft: '1.1rem' }}>
                  {(graph.change_requests as { display_name?: string; url?: string | null; number?: number }[]).map(
                    (cr, i) => (
                      <li key={`${cr.number ?? i}`}>
                        {cr.url ? (
                          <a href={cr.url} rel="noreferrer" target="_blank">
                            {cr.display_name ?? `PR/MR ${cr.number ?? ''}`}
                          </a>
                        ) : (
                          <span>{cr.display_name ?? `PR/MR ${cr.number ?? ''}`}</span>
                        )}
                      </li>
                    ),
                  )}
                </ul>
              ) : null}
              {(graph.branches as { display_name?: string }[])?.length ? (
                <p style={{ margin: '0.35rem 0' }}>
                  <strong>Branches:</strong>{' '}
                  {(graph.branches as { display_name?: string }[])
                    .map((b) => b.display_name)
                    .filter(Boolean)
                    .join(', ')}
                </p>
              ) : null}
              {(graph.commits as { short_sha?: string }[])?.length ? (
                <p style={{ margin: '0.35rem 0' }}>
                  <strong>Commits:</strong>{' '}
                  {(graph.commits as { short_sha?: string }[])
                    .map((c) => c.short_sha)
                    .filter(Boolean)
                    .join(', ')}
                </p>
              ) : null}
            </div>
          ) : null}
          {repoCx ? (
            <div className="forge-support">
              {repoCx.project_href ? (
                <p style={{ marginTop: 0 }}>
                  <Link className="le-btn le-btn--small" to={String(repoCx.project_href)}>
                    Repository dashboard (PRs, protection, planning links)
                  </Link>
                </p>
              ) : null}
              {(() => {
                const link = repoCx.work_item_link as Record<string, unknown> | undefined
                if (!link) return null
                return (
                  <p style={{ margin: '0.5rem 0' }}>
                    <strong>Fixture link:</strong>{' '}
                    {link.branch_url ? (
                      <a href={String(link.branch_url)} rel="noreferrer" target="_blank">
                        Branch {String(link.branch_name ?? '')}
                      </a>
                    ) : null}
                    {link.branch_url && link.pr_url ? ' · ' : null}
                    {link.pr_url ? (
                      <a href={String(link.pr_url)} rel="noreferrer" target="_blank">
                        PR/MR #{String(link.pull_request_number ?? '')}
                      </a>
                    ) : null}
                  </p>
                )
              })()}
              {(repoCx.open_pull_requests_preview as Record<string, unknown>[])?.length ? (
                <div className="le-table-wrap" style={{ marginTop: '0.5rem' }}>
                  <table className="le-table">
                    <thead>
                      <tr>
                        <th scope="col">PR</th>
                        <th scope="col">Status</th>
                        <th scope="col">Merge</th>
                        <th scope="col">Stale (d)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(repoCx.open_pull_requests_preview as Record<string, unknown>[]).map((pr, idx) => (
                        <tr key={String(pr.number ?? pr.id ?? idx)}>
                          <td>
                            {pr.url ? (
                              <a href={String(pr.url)} rel="noreferrer" target="_blank">
                                #{String(pr.number ?? '')}
                              </a>
                            ) : (
                              `#${String(pr.number ?? '')}`
                            )}
                          </td>
                          <td>{String(pr.state ?? '')}</td>
                          <td>{String(pr.mergeable ?? '')}</td>
                          <td>{pr.stale_days != null ? String(pr.stale_days) : '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : null}
              {repoCx.code_owners &&
              typeof repoCx.code_owners === 'object' &&
              (repoCx.code_owners as { present?: boolean }).present ? (
                <p style={{ margin: '0.5rem 0' }}>
                  <strong>CODEOWNERS:</strong>{' '}
                  {(repoCx.code_owners as { url?: string }).url ? (
                    <a href={String((repoCx.code_owners as { url?: string }).url)} rel="noreferrer" target="_blank">
                      configured
                    </a>
                  ) : (
                    'present'
                  )}
                </p>
              ) : null}
            </div>
          ) : null}
        </section>
      ) : null}

      {cicd && cicd.ok === false ? (
        <section className="le-story-hub-panel__block" aria-labelledby="le-sh-cicd-err">
          <h3 id="le-sh-cicd-err" className="le-story-hub-panel__h">
            Build and deploy trace
          </h3>
          <p className="forge-support">
            Trace unavailable: <code className="le-mono">{String(cicd.error ?? 'unknown')}</code>
          </p>
        </section>
      ) : cicd && cicd.ok !== false ? (
        <section className="le-story-hub-panel__block" aria-labelledby="le-sh-cicd">
          <h3 id="le-sh-cicd" className="le-story-hub-panel__h">
            Build and deploy trace
          </h3>
          <p className="forge-support" style={{ marginTop: 0 }}>
            Orchestration graph: story → build → artifact → release → environment (
            <code className="le-mono">tests</code>, <code className="le-mono">contains</code>,{' '}
            <code className="le-mono">deploys</code> edges).
          </p>
          {!cicd.linked ? (
            <p className="forge-support">This work item is not linked to builds in the graph yet.</p>
          ) : (
            <>
              {entityList(
                'Builds',
                (cicd.builds as { entity_id?: string; display_name?: unknown; external_ref?: unknown }[]) ?? [],
              )}
              {entityList(
                'Artifacts',
                (cicd.artifacts as { entity_id?: string; display_name?: unknown; external_ref?: unknown }[]) ?? [],
              )}
              {entityList(
                'Releases',
                (cicd.releases as { entity_id?: string; display_name?: unknown; external_ref?: unknown }[]) ?? [],
              )}
              {(cicd.deployments as Record<string, unknown>[])?.length ? (
                <div style={{ marginTop: '0.5rem' }}>
                  <strong>Deployments</strong>
                  <ul className="le-list" style={{ margin: '0.25rem 0', paddingLeft: '1.1rem' }}>
                    {((cicd.deployments as Record<string, unknown>[]) ?? []).map((dep, i) => (
                      <li key={`${dep.environment_entity_id ?? i}`}>
                        Release <code className="le-mono">{String(dep.release_entity_id ?? '')}</code> →{' '}
                        {String(dep.environment_name ?? dep.environment_entity_id ?? 'environment')}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {!(
                (cicd.builds as unknown[])?.length ||
                (cicd.artifacts as unknown[])?.length ||
                (cicd.releases as unknown[])?.length ||
                (cicd.deployments as unknown[])?.length
              ) ? (
                <p className="forge-support">Linked in the graph, but no build or deploy chain found yet.</p>
              ) : null}
            </>
          )}
        </section>
      ) : null}

      {qtrace && qtrace.ok === false ? (
        <section className="le-story-hub-panel__block" aria-labelledby="le-sh-qtrace-err">
          <h3 id="le-sh-qtrace-err" className="le-story-hub-panel__h">
            Test and defect trace
          </h3>
          <p className="forge-support">
            Trace unavailable: <code className="le-mono">{String(qtrace.error ?? 'unknown')}</code>
          </p>
        </section>
      ) : qtrace && qtrace.ok !== false ? (
        <section className="le-story-hub-panel__block" aria-labelledby="le-sh-qtrace">
          <h3 id="le-sh-qtrace" className="le-story-hub-panel__h">
            Test and defect trace
          </h3>
          <p className="forge-support" style={{ marginTop: 0 }}>
            Graph: test case → story (<code className="le-mono">validates</code>), defect → release (
            <code className="le-mono">raised_defect</code>, <code className="le-mono">affects</code>).
          </p>
          {!qtrace.linked ? (
            <p className="forge-support">Not linked to test cases in the graph yet.</p>
          ) : (
            <>
              {entityList(
                'Test plans',
                (qtrace.test_plans as { entity_id?: string; display_name?: unknown; external_ref?: unknown }[]) ??
                  [],
              )}
              {entityList(
                'Test suites',
                (qtrace.test_suites as { entity_id?: string; display_name?: unknown; external_ref?: unknown }[]) ??
                  [],
              )}
              {entityList(
                'Test cases',
                (qtrace.test_cases as { entity_id?: string; display_name?: unknown; external_ref?: unknown }[]) ?? [],
              )}
              {entityList(
                'Test runs',
                (qtrace.test_runs as { entity_id?: string; display_name?: unknown; external_ref?: unknown }[]) ?? [],
              )}
              {entityList(
                'Defects',
                (qtrace.defects as { entity_id?: string; display_name?: unknown; external_ref?: unknown }[]) ?? [],
              )}
              {entityList(
                'Affected releases',
                (qtrace.releases as { entity_id?: string; display_name?: unknown; external_ref?: unknown }[]) ?? [],
              )}
            </>
          )}
        </section>
      ) : null}

      {qevidence && qevidence.ok === true && (qevidence.test_cases as unknown[])?.length ? (
        <section className="le-story-hub-panel__block" aria-labelledby="le-sh-qev">
          <h3 id="le-sh-qev" className="le-story-hub-panel__h">
            Test evidence (fixture)
          </h3>
          <p className="forge-support" style={{ marginTop: 0 }}>
            From <code className="le-mono">test-quality.json</code> / demo seed: cases, runs, defects, UAT, attachments.
          </p>
          <ul className="le-list" style={{ margin: '0.25rem 0', paddingLeft: '1.1rem' }}>
            {(qevidence.test_cases as { id?: string; title?: string }[]).map((tc) => (
              <li key={tc.id}>
                <code className="le-mono">{tc.id}</code>
                {tc.title ? <> · {tc.title}</> : null}
              </li>
            ))}
          </ul>
          {(qevidence.test_runs_preview as { id?: string; status?: string }[])?.length ? (
            <div style={{ marginTop: '0.5rem' }}>
              <strong>Recent runs</strong>
              <ul className="le-list" style={{ margin: '0.25rem 0', paddingLeft: '1.1rem' }}>
                {((qevidence.test_runs_preview as { id?: string; status?: string }[]) ?? []).map((r) => (
                  <li key={r.id}>
                    <code className="le-mono">{r.id}</code> — {r.status ?? '—'}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          {(qevidence.defects as { id?: string; title?: string; status?: string }[])?.length ? (
            <div style={{ marginTop: '0.5rem' }}>
              <strong>Defects</strong>
              <ul className="le-list" style={{ margin: '0.25rem 0', paddingLeft: '1.1rem' }}>
                {((qevidence.defects as { id?: string; title?: string; status?: string }[]) ?? []).map((d) => (
                  <li key={d.id}>
                    <code className="le-mono">{d.id}</code>
                    {d.title ? <> · {d.title}</> : null} — {d.status ?? '—'}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          {(qevidence.uat_signoffs as { status?: string; by?: string }[])?.length ? (
            <p style={{ marginTop: '0.5rem' }}>
              <strong>UAT:</strong>{' '}
              {(qevidence.uat_signoffs as { status?: string; by?: string }[])
                .map((u) => `${u.status ?? ''}${u.by ? ` (${u.by})` : ''}`)
                .join('; ')}
            </p>
          ) : null}
          {(qevidence.evidence_attachments as { label?: string; url?: string }[])?.length ? (
            <div style={{ marginTop: '0.5rem' }}>
              <strong>Attachments</strong>
              <ul className="le-list" style={{ margin: '0.25rem 0', paddingLeft: '1.1rem' }}>
                {((qevidence.evidence_attachments as { label?: string; url?: string }[]) ?? []).map((a) => (
                  <li key={a.url ?? a.label}>
                    {a.url ? (
                      <a href={a.url} rel="noreferrer" target="_blank">
                        {a.label ?? a.url}
                      </a>
                    ) : (
                      (a.label ?? '—') as string
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </section>
      ) : null}

      {strace && strace.ok === false ? (
        <section className="le-story-hub-panel__block" aria-labelledby="le-sh-strace-err">
          <h3 id="le-sh-strace-err" className="le-story-hub-panel__h">
            Security &amp; compliance trace
          </h3>
          <p className="forge-support">
            Trace unavailable: <code className="le-mono">{String(strace.error ?? 'unknown')}</code>
          </p>
        </section>
      ) : strace && strace.ok !== false ? (
        <section className="le-story-hub-panel__block" aria-labelledby="le-sh-strace">
          <h3 id="le-sh-strace" className="le-story-hub-panel__h">
            Security &amp; compliance trace
          </h3>
          <p className="forge-support" style={{ marginTop: 0 }}>
            Graph: security finding <code className="le-mono">affects</code> story; exception{' '}
            <code className="le-mono">accepted_risk_for</code> finding; control <code className="le-mono">satisfies</code>{' '}
            release.
          </p>
          {!strace.linked ? (
            <p className="forge-support">Story not linked in the orchestration graph yet.</p>
          ) : (
            <>
              {entityList(
                'Security findings',
                (strace.security_findings as { entity_id?: string; display_name?: unknown; external_ref?: unknown }[]) ??
                  [],
              )}
              {entityList(
                'Compliance exceptions (accepted risk)',
                (strace.compliance_exceptions as {
                  entity_id?: string
                  display_name?: unknown
                  external_ref?: unknown
                }[]) ?? [],
              )}
              {entityList(
                'Controls for releases',
                (strace.controls_for_releases as {
                  entity_id?: string
                  display_name?: unknown
                  external_ref?: unknown
                }[]) ?? [],
              )}
              {entityList(
                'Releases (from delivery)',
                (strace.releases_from_delivery as {
                  entity_id?: string
                  display_name?: unknown
                  external_ref?: unknown
                }[]) ?? [],
              )}
            </>
          )}
        </section>
      ) : null}

      {(() => {
        const deOk = sevidence && sevidence.ok === true
        const sf = (sevidence?.security_findings as unknown[])?.length ?? 0
        const vv = (sevidence?.vulnerabilities as unknown[])?.length ?? 0
        const ss = (sevidence?.secret_exposures as unknown[])?.length ?? 0
        const ex = (sevidence?.exceptions as unknown[])?.length ?? 0
        const cc = (sevidence?.controls as unknown[])?.length ?? 0
        const hasDe = deOk && sf + vv + ss + ex + cc > 0
        return hasDe ? (
          <section className="le-story-hub-panel__block" aria-labelledby="le-sh-de">
            <h3 id="le-sh-de" className="le-story-hub-panel__h">
              DevSecOps evidence (fixture)
            </h3>
            <p className="forge-support" style={{ marginTop: 0 }}>
              From <code className="le-mono">devsecops-compliance.json</code> / demo seed — findings, vulns, secrets,
              exceptions, and controls tagged to this story.
            </p>
            {sf ? (
              <div style={{ marginTop: '0.5rem' }}>
                <strong>Findings</strong>
                <ul className="le-list" style={{ margin: '0.25rem 0', paddingLeft: '1.1rem' }}>
                  {((sevidence?.security_findings as { finding_id?: string; title?: string; severity?: string }[]) ?? []).map(
                    (f) => (
                      <li key={f.finding_id}>
                        <code className="le-mono">{f.finding_id}</code>
                        {f.title ? <> · {f.title}</> : null}
                        {f.severity ? (
                          <span className="forge-support"> — {f.severity}</span>
                        ) : null}
                      </li>
                    ),
                  )}
                </ul>
              </div>
            ) : null}
            {vv ? (
              <div style={{ marginTop: '0.5rem' }}>
                <strong>Vulnerabilities</strong>
                <ul className="le-list" style={{ margin: '0.25rem 0', paddingLeft: '1.1rem' }}>
                  {((sevidence?.vulnerabilities as { vuln_id?: string; cve_id?: string; title?: string }[]) ?? []).map(
                    (v) => (
                      <li key={v.vuln_id ?? v.cve_id}>
                        <code className="le-mono">{v.cve_id ?? v.vuln_id}</code>
                        {v.title ? <> · {v.title}</> : null}
                      </li>
                    ),
                  )}
                </ul>
              </div>
            ) : null}
            {ss ? (
              <div style={{ marginTop: '0.5rem' }}>
                <strong>Secret exposures</strong>
                <ul className="le-list" style={{ margin: '0.25rem 0', paddingLeft: '1.1rem' }}>
                  {((sevidence?.secret_exposures as { exposure_id?: string; path?: string }[]) ?? []).map((s) => (
                    <li key={s.exposure_id}>
                      <code className="le-mono">{s.exposure_id}</code>
                      {s.path ? <> · {s.path}</> : null}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
            {ex ? (
              <div style={{ marginTop: '0.5rem' }}>
                <strong>Exceptions</strong>
                <ul className="le-list" style={{ margin: '0.25rem 0', paddingLeft: '1.1rem' }}>
                  {((sevidence?.exceptions as { id?: string; exception_id?: string; owner?: string; expires_at?: string }[]) ?? []).map(
                    (e) => (
                      <li key={e.exception_id ?? e.id}>
                        <code className="le-mono">{e.exception_id ?? e.id}</code>
                        {e.owner ? <> · owner {e.owner}</> : null}
                        {e.expires_at ? (
                          <span className="forge-support"> · expires {e.expires_at}</span>
                        ) : null}
                      </li>
                    ),
                  )}
                </ul>
              </div>
            ) : null}
            {cc ? (
              <div style={{ marginTop: '0.5rem' }}>
                <strong>Controls</strong>
                <ul className="le-list" style={{ margin: '0.25rem 0', paddingLeft: '1.1rem' }}>
                  {((sevidence?.controls as { control_id?: string; name?: string }[]) ?? []).map((c) => (
                    <li key={c.control_id}>
                      <code className="le-mono">{c.control_id}</code>
                      {c.name ? <> · {c.name}</> : null}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </section>
        ) : null
      })()}

      {otrace && otrace.ok === false ? (
        <section className="le-story-hub-panel__block" aria-labelledby="le-sh-otrace-err">
          <h3 id="le-sh-otrace-err" className="le-story-hub-panel__h">
            Ops &amp; production trace
          </h3>
          <p className="forge-support">
            Trace unavailable: <code className="le-mono">{String(otrace.error ?? 'unknown')}</code>
          </p>
        </section>
      ) : otrace && otrace.ok !== false ? (
        <section className="le-story-hub-panel__block" aria-labelledby="le-sh-otrace">
          <h3 id="le-sh-otrace" className="le-story-hub-panel__h">
            Ops &amp; production trace
          </h3>
          <p className="forge-support" style={{ marginTop: 0 }}>
            Graph: incident <code className="le-mono">affects</code> story; <code className="le-mono">triggered_after</code>{' '}
            release; <code className="le-mono">impacts</code> service; postmortem <code className="le-mono">analyzes</code>{' '}
            incident.
          </p>
          {!otrace.linked ? (
            <p className="forge-support">Story not linked in the orchestration graph yet.</p>
          ) : (
            <>
              {entityList(
                'Incidents',
                (otrace.incidents as { entity_id?: string; display_name?: unknown; external_ref?: unknown }[]) ?? [],
              )}
              {entityList(
                'Releases (from incidents)',
                (otrace.releases_from_incidents as {
                  entity_id?: string
                  display_name?: unknown
                  external_ref?: unknown
                }[]) ?? [],
              )}
              {entityList(
                'Services impacted',
                (otrace.services_impacted as { entity_id?: string; display_name?: unknown; external_ref?: unknown }[]) ??
                  [],
              )}
              {entityList(
                'Postmortems',
                (otrace.postmortems as { entity_id?: string; display_name?: unknown; external_ref?: unknown }[]) ?? [],
              )}
            </>
          )}
        </section>
      ) : null}

      {(() => {
        const ox = oevidence && oevidence.ok === true
        const oi = (oevidence?.incidents as unknown[])?.length ?? 0
        const op = (oevidence?.postmortems as unknown[])?.length ?? 0
        const os = (oevidence?.slos as unknown[])?.length ?? 0
        const hasOx = ox && oi + op + os > 0
        return hasOx ? (
          <section className="le-story-hub-panel__block" aria-labelledby="le-sh-ops-ev">
            <h3 id="le-sh-ops-ev" className="le-story-hub-panel__h">
              Ops delivery evidence (fixture)
            </h3>
            <p className="forge-support" style={{ marginTop: 0 }}>
              From <code className="le-mono">ops-delivery.json</code> / demo seed — incidents, postmortems, and SLOs tied
              to this story id.
            </p>
            {oi ? (
              <ul className="le-list" style={{ margin: '0.25rem 0', paddingLeft: '1.1rem' }}>
                {((oevidence?.incidents as { incident_id?: string; title?: string; status?: string }[]) ?? []).map(
                  (x) => (
                    <li key={x.incident_id}>
                      <code className="le-mono">{x.incident_id}</code>
                      {x.title ? <> · {x.title}</> : null}
                      {x.status ? <span className="forge-support"> — {x.status}</span> : null}
                    </li>
                  ),
                )}
              </ul>
            ) : null}
            {op ? (
              <div style={{ marginTop: '0.5rem' }}>
                <strong>Postmortems</strong>
                <ul className="le-list" style={{ margin: '0.25rem 0', paddingLeft: '1.1rem' }}>
                  {((oevidence?.postmortems as { postmortem_id?: string; summary?: string }[]) ?? []).map((p) => (
                    <li key={p.postmortem_id}>
                      <code className="le-mono">{p.postmortem_id}</code>
                      {p.summary ? <> · {p.summary.slice(0, 120)}</> : null}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
            {os ? (
              <div style={{ marginTop: '0.5rem' }}>
                <strong>SLOs</strong>
                <ul className="le-list" style={{ margin: '0.25rem 0', paddingLeft: '1.1rem' }}>
                  {((oevidence?.slos as { slo_id?: string; target_percent?: number }[]) ?? []).map((s) => (
                    <li key={s.slo_id}>
                      <code className="le-mono">{s.slo_id}</code>
                      {s.target_percent != null ? (
                        <span className="forge-support"> — target {s.target_percent}%</span>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </section>
        ) : null
      })()}

      {slotEntries.length > 0 && (
        <section className="le-story-hub-panel__block" aria-labelledby="le-sh-slots">
          <h3 id="le-sh-slots" className="le-story-hub-panel__h">
            Details
          </h3>
          <div className="le-table-wrap">
            <table className="le-table">
              <tbody>
                {slotEntries.map(([k, v]) => (
                  <tr key={k}>
                    <th className="le-story-hub-panel__slot-th">{k.replace(/_/g, ' ')}</th>
                    <td>
                      <MarkdownBody text={storySlotCellToMarkdown(v)} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {!defText &&
        slotEntries.length === 0 &&
        tasks.length === 0 &&
        strace == null &&
        !(sevidence && sevidence.ok === true) &&
        otrace == null &&
        !(oevidence && oevidence.ok === true) &&
        !(qevidence && qevidence.ok === true) &&
        qtrace == null && (
        <p className="forge-support">No structured story content in this payload.</p>
      )}
    </div>
  )
}
