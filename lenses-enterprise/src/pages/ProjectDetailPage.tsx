import { useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useResilientJsonBlock } from '../hooks/useResilientJsonBlock'
import { ProjectAtAGlance, ProjectLocalNav } from '../components/projects'
import {
  DataResilienceBar,
  ObjectMetaBar,
  PageHeader,
  StatePanel,
  TechnicalDetails,
} from '../components/page'
import { chargeMdCandidates } from '../lib/copilotPageEvidence'
import { PROJECT_COPILOT_DEFAULT, PROJECT_OBJECT_HOME, ROUTE_SUBTITLE, STUDIO_VOCAB } from '../nav/studioVisibleCopy'
import { DocsHealthProjectCard } from '../components/docs-health/DocsHealthProjectCard'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'
import { TraceabilityLaunchButton } from '../components/traceability'
import { HandoffLoopPanel, OutcomeLoopPanel } from '../components/plan'
import { DEMO_ORCHESTRATION_STORY_ID, demoRepoEntityId } from '../constants/demoOrchestration'

type ProjectStats = {
  commits_total?: number | null
  tracked_files?: number
  tracked_lines_approx?: number
  contributors?: { commits: number; name: string }[]
  extensions?: { extension: string; count: number }[]
}

type RwHealth = {
  open_prs_count?: number
  stale_open_prs_count?: number
  blocked_merge_count?: number
  review_debt_total?: number
  unlinked_work_items_count?: number
}

type RwPull = {
  number?: number
  title?: string
  state?: string
  mergeable?: string
  stale_days?: number | null
  url?: string
  review_debt_count?: number
  merge_blocked_reason?: string | null
  head_ref?: string
}

type RepoWorkflowProjectPayload = {
  ok?: boolean
  feature_enabled?: boolean
  project?: string
  repo?: {
    project?: string
    provider?: string
    health?: RwHealth
    workflow?: {
      repository?: { web_url?: string; full_name?: string; default_branch?: string }
      pull_requests?: RwPull[]
      branch_protection?: { pattern?: string; required_reviews?: number; url?: string }[]
      code_owners?: { present?: boolean; url?: string | null; path?: string | null }
    }
    work_item_links?: {
      story_id?: string
      pr_url?: string
      branch_url?: string
      branch_name?: string
      pull_request_number?: number
    }[]
    data_sources?: string[]
  } | null
  hints?: string[]
}

type ProjectQualityPayload = {
  ok?: boolean
  feature_enabled?: boolean
  provider_kind?: string
  project?: string
  quality_summary?: {
    open_defects?: number
    failed_gates?: number
    gates_passed?: number
    latest_run_by_suite?: Record<string, { status?: string; id?: string }>
    release_quality?: { ready?: boolean; summary?: string }
  } | null
  gate_evaluations?: { name?: string; passed?: boolean }[]
  hints?: string[]
}

type ProjectDevsecopsPayload = {
  ok?: boolean
  feature_enabled?: boolean
  provider_kind?: string
  project?: string
  security_summary?: {
    risk_score?: { value?: number }
    security_release_gate?: { passed?: boolean; summary?: string }
    rollup_repo?: { weighted_open_score?: number; open_security_findings?: number }
  } | null
  policy_check_evaluations?: { passed?: boolean }[]
  hints?: string[]
}

type ProjectContext = {
  ok?: boolean
  project?: string
  role?: string
  session_login?: string | null
  access_policy_enforced?: boolean
  can_read_project?: boolean
  can_write_project?: boolean
  effective_readonly?: boolean
  is_workspace_super_admin?: boolean
  git_user_name?: string
  git_user_email?: string
}

export function ProjectDetailPage() {
  const { name = '' } = useParams()
  const decoded = decodeURIComponent(name)
  const enc = encodeURIComponent(decoded)

  const copilotScope = useMemo(
    () => ({
      pageContextSummary: decoded
        ? `Forge Studio · Project dashboard · repository ${decoded}`
        : 'Forge Studio · Project dashboard',
      relatedMdRelPaths: chargeMdCandidates(decoded || undefined),
    }),
    [decoded],
  )

  useLensesCopilotPage({
    route: 'projects',
    projectSlug: decoded || undefined,
    scopeSite: decoded || undefined,
    defaultQuery: PROJECT_COPILOT_DEFAULT,
    pageContextSummary: copilotScope.pageContextSummary,
    relatedMdRelPaths: copilotScope.relatedMdRelPaths,
  })

  const statsUrl = decoded ? `/api/project/${enc}/stats` : null
  const ctxUrl = decoded ? `/api/project/${enc}/context` : null
  const rwUrl = decoded ? `/api/project/${enc}/repo-workflow` : null
  const pqUrl = decoded ? `/api/project/${enc}/quality` : null
  const dsUrl = decoded ? `/api/project/${enc}/devsecops` : null

  const stats = useResilientJsonBlock<ProjectStats>(statsUrl, {
    snapshotKey: `project-stats:${decoded}`,
  })
  const ctx = useResilientJsonBlock<ProjectContext>(ctxUrl, {
    snapshotKey: `project-context:${decoded}`,
  })
  const rw = useResilientJsonBlock<RepoWorkflowProjectPayload>(rwUrl, {
    snapshotKey: `project-repo-workflow:${decoded}`,
  })
  const pq = useResilientJsonBlock<ProjectQualityPayload>(pqUrl, {
    snapshotKey: `project-quality:${decoded}`,
  })
  const ds = useResilientJsonBlock<ProjectDevsecopsPayload>(dsUrl, {
    snapshotKey: `project-devsecops:${decoded}`,
  })

  const totalFailure =
    Boolean(decoded) &&
    stats.phase === 'error' &&
    !stats.data &&
    ctx.phase === 'error' &&
    !ctx.data

  const retryBoth = () => {
    stats.retry()
    ctx.retry()
    rw.retry()
    pq.retry()
    ds.retry()
  }

  const statsPayload = stats.data
  const ctxPayload = ctx.data
  const readonlyRisk =
    Boolean(decoded) &&
    (Boolean(ctxPayload?.effective_readonly) || ctxPayload?.can_write_project === false)

  const evidenceHref = decoded ? `/workspace-md?contextProject=${enc}` : '/workspace-md'

  const { riskLines, nextAction } = useMemo(() => {
    if (!decoded) {
      return {
        riskLines: [] as string[],
        nextAction: {
          title: PROJECT_OBJECT_HOME.evidenceLinkLabel,
          description: 'Pick a repository from the projects list.',
          to: '/projects',
        },
      }
    }
    const lines: string[] = []
    const h = rw.data?.repo?.health
    const failedGates = pq.data?.quality_summary?.failed_gates ?? 0
    const secFail = ds.data?.security_summary?.security_release_gate?.passed === false
    const blockedPrs = h?.blocked_merge_count ?? 0
    const stalePrs = h?.stale_open_prs_count ?? 0
    if (failedGates > 0) {
      lines.push(`${failedGates} quality gate(s) failing — review before promoting work.`)
    }
    if (secFail) {
      lines.push('Security release gate not passing — review findings and exceptions.')
    }
    if (blockedPrs > 0) {
      lines.push(`${blockedPrs} open PR(s) blocked on merge — unblock reviews or branch rules.`)
    } else if (stalePrs > 0) {
      lines.push(`${stalePrs} PR(s) stale (open ≥7d) — review or close to reduce debt.`)
    }

    let next: { title: string; description: string; to: string }
    if (readonlyRisk) {
      next = {
        title: PROJECT_OBJECT_HOME.evidenceLinkLabel,
        description:
          'Review indexed charge logs and journals in read-only — session and write access are under Inspect on this page.',
        to: evidenceHref,
      }
    } else if (failedGates > 0 || blockedPrs > 0 || stalePrs >= 3) {
      next = {
        title: `Open ${STUDIO_VOCAB.repositoryCharts}`,
        description: 'Inspect PR health, review debt, and quality blocks with the same repository scope.',
        to: `/projects/${enc}/charts`,
      }
    } else {
      next = {
        title: PROJECT_OBJECT_HOME.evidenceLinkLabel,
        description: 'Open indexed charge logs and journals — pick a file from the list without typing paths.',
        to: evidenceHref,
      }
    }
    return { riskLines: lines, nextAction: next }
  }, [decoded, readonlyRisk, rw.data, pq.data, ds.data, evidenceHref, enc])

  if (!decoded) {
    return (
      <StatePanel
        variant="invalid"
        title="Missing project name"
        description="Use a URL like /studio/projects/my-repo, or pick a repository from the projects list."
        actions={<Link to="/projects">All projects</Link>}
      />
    )
  }

  const contrib = statsPayload?.contributors ?? []
  const exts = statsPayload?.extensions ?? []

  return (
    <>
      <PageHeader
        title={decoded}
        purpose={ROUTE_SUBTITLE.projectDashboard}
        preface={
          <Link to="/projects" className="forge-support">
            ← {STUDIO_VOCAB.projects}
          </Link>
        }
        primaryAction={
          <Link className="le-btn le-btn--primary" to={`/projects/${enc}/charts`}>
            {STUDIO_VOCAB.repositoryCharts}
          </Link>
        }
        secondaryMenuItems={[
          { key: 'strategy', label: STUDIO_VOCAB.architectureStrategy, to: `/projects/${enc}/strategy` },
          { key: 'docs', label: STUDIO_VOCAB.docsHealth, to: `/projects/${enc}/docs-health` },
          { key: 'evidence', label: STUDIO_VOCAB.projectEvidenceBrowse, to: evidenceHref },
        ]}
      />

      <ProjectLocalNav projectName={decoded} />

      {!totalFailure ? (
        <ProjectAtAGlance
          encodedProject={enc}
          projectName={decoded}
          evidenceHref={evidenceHref}
          riskLines={riskLines}
          nextAction={nextAction}
          metricCommits={statsPayload?.commits_total ?? '—'}
          metricFiles={statsPayload?.tracked_files ?? '—'}
          metricOpenPrs={rw.data?.repo?.health?.open_prs_count ?? '—'}
          workItemLinks={rw.data?.repo?.work_item_links ?? []}
        />
      ) : null}

      {!totalFailure ? <DocsHealthProjectCard projectName={decoded} /> : null}

      {totalFailure ? (
        <DataResilienceBar
          variant="error"
          failure={{
            kind: 'unknown',
            summary: 'Neither repository stats nor access context could be loaded.',
            detail: [stats.failure?.detail, ctx.failure?.detail].filter(Boolean).join(' · ') || undefined,
          }}
          snapshotAtMs={null}
          snapshotTimeLabel={null}
          snapshotAgeLabel={null}
          onRetry={retryBoth}
          extraActions={
            <>
              <Link className="le-btn le-btn--small" to="/projects">
                All projects
              </Link>
              <a className="le-btn le-btn--small" href={`/projects/${enc}`}>
                Classic UI
              </a>
            </>
          }
        />
      ) : null}

      {ctxPayload ? (
        <TechnicalDetails summary="Session, access & identity (inspect)" defaultOpen={false}>
          {readonlyRisk ? (
            <p className="forge-support" style={{ marginTop: 0 }}>
              {PROJECT_OBJECT_HOME.accessRiskReadonly} Use{' '}
              <a className="le-btn le-btn--small" href={`/projects/${enc}`}>
                legacy full project page
              </a>{' '}
              only if you need controls that are not in Studio yet.
            </p>
          ) : null}
          <ObjectMetaBar
            label="Project identity & access"
            items={[
              { label: 'Session', value: ctxPayload.session_login ?? '(none)' },
              {
                label: 'Access',
                value: `${ctxPayload.can_read_project ? 'read' : 'no read'} · ${ctxPayload.can_write_project ? 'write' : 'read-only'}`,
              },
              ...(ctxPayload.role ? [{ label: 'Role', value: ctxPayload.role }] : []),
            ]}
          />
          <ul className="le-list" style={{ fontSize: '0.85rem', listStyle: 'none', paddingLeft: 0, marginTop: '0.75rem' }}>
            <li>
              <strong>Policy:</strong> {ctxPayload.access_policy_enforced ? 'enforced' : 'open / legacy'}
            </li>
            {ctxPayload.is_workspace_super_admin ? (
              <li>
                <strong>Workspace super admin</strong>
              </li>
            ) : null}
            {(ctxPayload.git_user_name || ctxPayload.git_user_email) && (
              <li>
                <strong>Git user:</strong> {ctxPayload.git_user_name ?? '—'}{' '}
                <span className="le-muted">&lt;{ctxPayload.git_user_email ?? '—'}&gt;</span>
              </li>
            )}
          </ul>
        </TechnicalDetails>
      ) : null}

      {!totalFailure && ctx.phase === 'error' && !ctxPayload ? (
        <DataResilienceBar
          variant="error"
          failure={ctx.failure}
          snapshotAtMs={null}
          snapshotTimeLabel={null}
          snapshotAgeLabel={null}
          onRetry={ctx.retry}
          extraActions={
            <Link className="le-btn le-btn--small" to="/projects">
              All projects
            </Link>
          }
        />
      ) : null}

      {!totalFailure && ctx.phase === 'stale' && ctxPayload ? (
        <DataResilienceBar
          variant="stale"
          failure={ctx.failure}
          snapshotAtMs={ctx.snapshotFetchedAt}
          snapshotTimeLabel={ctx.snapshotTimeLabel}
          snapshotAgeLabel={ctx.snapshotAgeLabel}
          onRetry={ctx.retry}
        />
      ) : null}

      <TechnicalDetails summary={`${PROJECT_OBJECT_HOME.nextStepsTitle} (inspect)`} defaultOpen={false}>
        <ul className="le-list" style={{ fontSize: '0.88rem', lineHeight: 1.55, margin: 0, paddingLeft: '1.2rem' }}>
          <li>
            Workspace-wide automation and cross-repository reporting live under{' '}
            <strong>Settings (gear)</strong> → Inspect &amp; advanced → Tools &amp; automation or Advanced reporting.
          </li>
          <li>
            Direct links still work: <Link to="/toolset">{STUDIO_VOCAB.toolset}</Link>,{' '}
            <Link to="/overview/charts">{STUDIO_VOCAB.advancedReporting}</Link>.
          </li>
        </ul>
      </TechnicalDetails>

      <section className="le-panel" style={{ marginBottom: '1rem' }}>
        <h2 className="le-panel__title">{PROJECT_OBJECT_HOME.healthSectionTitle}</h2>

        {stats.phase === 'loading' && !statsPayload ? (
          <StatePanel
            variant="loading"
            density="compact"
            title="Loading repository stats"
            description="Commits, files, and contributor roll-up from your workspace scan."
          />
        ) : null}

        {!totalFailure && stats.phase === 'error' && !statsPayload ? (
          <DataResilienceBar
            variant="error"
            failure={stats.failure}
            snapshotAtMs={null}
            snapshotTimeLabel={null}
            snapshotAgeLabel={null}
            onRetry={stats.retry}
            extraActions={
              <>
                <Link className="le-btn le-btn--small" to="/projects">
                  All projects
                </Link>
                <a className="le-btn le-btn--small" href={`/projects/${enc}`}>
                  Classic UI
                </a>
              </>
            }
          />
        ) : null}

        {!totalFailure && stats.phase === 'stale' && statsPayload ? (
          <DataResilienceBar
            variant="stale"
            failure={stats.failure}
            snapshotAtMs={stats.snapshotFetchedAt}
            snapshotTimeLabel={stats.snapshotTimeLabel}
            snapshotAgeLabel={stats.snapshotAgeLabel}
            onRetry={stats.retry}
          />
        ) : null}

        {statsPayload ? (
          <>
            <p className="forge-support" style={{ marginTop: 0 }}>
              {PROJECT_OBJECT_HOME.healthSectionLead}
            </p>
            {rw.data?.feature_enabled && rw.data.repo?.workflow && rw.data.repo.data_sources?.includes('local_fixture') ? (
              <div style={{ marginBottom: '1rem' }}>
                <h3 className="le-panel__title" style={{ fontSize: '1rem', marginBottom: '0.35rem' }}>
                  Pull requests &amp; merge health
                </h3>
                <TechnicalDetails summary="Adapter &amp; fixture detail (inspect)" defaultOpen={false}>
                  <p className="forge-support" style={{ marginTop: 0 }}>
                    PR/MR and branch data from <code className="le-mono">repo-workflow.json</code> / demo seed — same
                    normalized contract as GitHub, GitLab, and Azure Repos adapters.
                  </p>
                </TechnicalDetails>
                <div className="le-stats">
                  <div className="le-stat">
                    <span className="le-stat__value">{rw.data.repo.health?.open_prs_count ?? 0}</span>
                    <span className="le-stat__label">Open PRs/MRs</span>
                  </div>
                  <div className="le-stat">
                    <span className="le-stat__value">{rw.data.repo.health?.stale_open_prs_count ?? 0}</span>
                    <span className="le-stat__label">Stale (≥7d)</span>
                  </div>
                  <div className="le-stat">
                    <span className="le-stat__value">{rw.data.repo.health?.blocked_merge_count ?? 0}</span>
                    <span className="le-stat__label">Blocked merge</span>
                  </div>
                  <div className="le-stat">
                    <span className="le-stat__value">{rw.data.repo.health?.review_debt_total ?? 0}</span>
                    <span className="le-stat__label">Review debt</span>
                  </div>
                  <div className="le-stat">
                    <span className="le-stat__value">
                      {rw.data.repo.health?.unlinked_work_items_count ?? '—'}
                    </span>
                    <span className="le-stat__label">Unlinked items</span>
                  </div>
                </div>
                {rw.data.repo.workflow.repository?.web_url ? (
                  <p style={{ marginTop: '0.5rem', marginBottom: 0 }}>
                    <a
                      className="le-btn le-btn--small"
                      href={rw.data.repo.workflow.repository.web_url}
                      rel="noreferrer"
                      target="_blank"
                    >
                      Open remote repository
                    </a>
                  </p>
                ) : null}
                {(rw.data.repo.workflow.pull_requests ?? []).filter((p) => (p.state || '').toLowerCase() === 'open')
                  .length > 0 ? (
                  <div className="le-table-wrap" style={{ marginTop: '0.75rem' }}>
                    <table className="le-table">
                      <thead>
                        <tr>
                          <th scope="col">PR</th>
                          <th scope="col">Branch</th>
                          <th scope="col">Merge</th>
                          <th scope="col">Reviews</th>
                          <th scope="col">Stale</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(rw.data.repo.workflow.pull_requests ?? [])
                          .filter((p) => (p.state || '').toLowerCase() === 'open')
                          .map((p) => (
                            <tr key={p.number ?? p.title}>
                              <td>
                                {p.url ? (
                                  <a href={p.url} rel="noreferrer" target="_blank">
                                    #{p.number ?? '—'}
                                  </a>
                                ) : (
                                  `#${p.number ?? '—'}`
                                )}
                                {p.title ? (
                                  <span className="le-muted" style={{ marginLeft: '0.35rem' }}>
                                    {p.title}
                                  </span>
                                ) : null}
                              </td>
                              <td className="le-mono" style={{ fontSize: '0.8rem' }}>
                                {p.head_ref ?? '—'}
                              </td>
                              <td>
                                {p.merge_blocked_reason ? (
                                  <span className="le-muted" title={p.merge_blocked_reason}>
                                    blocked
                                  </span>
                                ) : (
                                  (p.mergeable || '—').toString()
                                )}
                              </td>
                              <td>{p.review_debt_count ?? 0}</td>
                              <td>{p.stale_days != null ? String(p.stale_days) : '—'}</td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  </div>
                ) : null}
              </div>
            ) : rw.phase === 'loading' && !rw.data ? (
              <p className="forge-support">Loading code workflow…</p>
            ) : null}
            <div className="le-stats">
              <div className="le-stat">
                <span className="le-stat__value">{statsPayload.commits_total ?? '—'}</span>
                <span className="le-stat__label">Commits (HEAD)</span>
              </div>
              <div className="le-stat">
                <span className="le-stat__value">{statsPayload.tracked_files ?? '—'}</span>
                <span className="le-stat__label">Tracked files</span>
              </div>
              <div className="le-stat">
                <span className="le-stat__value">{contrib.length}</span>
                <span className="le-stat__label">Contributors (90d)</span>
              </div>
              {statsPayload.tracked_lines_approx != null && (
                <div className="le-stat">
                  <span className="le-stat__value">{statsPayload.tracked_lines_approx.toLocaleString()}</span>
                  <span className="le-stat__label">Lines (approx.)</span>
                </div>
              )}
            </div>

            {pq.data?.feature_enabled === false ? (
              <p className="forge-support" style={{ marginTop: '0.75rem' }}>
                Quality gates API disabled on server.
              </p>
            ) : pq.data?.provider_kind === 'local_fixture' && pq.data?.quality_summary ? (
              <div style={{ marginTop: '1rem' }}>
                <h3 className="le-panel__title" style={{ fontSize: '1rem', marginBottom: '0.35rem' }}>
                  Quality &amp; tests (next to pipeline signals)
                </h3>
                <p className="forge-support" style={{ marginTop: 0 }}>
                  From <code className="le-mono">test-quality.json</code> / demo seed — same release gate model as
                  Plan → Today. Failed gates block promotions in the CI/CD control tower.
                </p>
                <div className="le-stats">
                  <div className="le-stat">
                    <span
                      className="le-stat__value"
                      style={{
                        color:
                          (pq.data.quality_summary?.failed_gates ?? 0) > 0
                            ? 'var(--le-danger, #c62828)'
                            : undefined,
                      }}
                    >
                      {pq.data.quality_summary?.failed_gates ?? 0}
                    </span>
                    <span className="le-stat__label">Gates failed</span>
                  </div>
                  <div className="le-stat">
                    <span className="le-stat__value">{pq.data.quality_summary?.open_defects ?? 0}</span>
                    <span className="le-stat__label">Open defects</span>
                  </div>
                  <div className="le-stat">
                    <span className="le-stat__value">
                      {pq.data.quality_summary?.release_quality?.ready === true
                        ? 'Yes'
                        : pq.data.quality_summary?.release_quality?.ready === false
                          ? 'No'
                          : '—'}
                    </span>
                    <span className="le-stat__label">Train ready</span>
                  </div>
                </div>
                {pq.data.quality_summary?.release_quality?.summary ? (
                  <p className="forge-support" style={{ marginBottom: 0 }}>
                    {pq.data.quality_summary.release_quality.summary}
                  </p>
                ) : null}
                <p style={{ marginTop: '0.5rem', marginBottom: 0 }}>
                  <Link className="le-btn le-btn--small" to="/plan?tab=today#le-quality-gates-h">
                    Open workspace quality card
                  </Link>
                </p>
                <TechnicalDetails summary="Quality API payload (inspect)" defaultOpen={false}>
                  <a className="le-btn le-btn--small" href={`/api/project/${enc}/quality`}>
                    Open raw JSON
                  </a>
                </TechnicalDetails>
              </div>
            ) : pq.phase === 'loading' && !pq.data ? (
              <p className="forge-support" style={{ marginTop: '0.75rem' }}>
                Loading quality summary…
              </p>
            ) : pq.data?.provider_kind === 'scan_only' ? (
              <p className="forge-support" style={{ marginTop: '0.75rem' }}>
                No test-quality fixture — set <code className="le-mono">LENSES_TEST_QUALITY_SEED_DEMO=1</code> or add{' '}
                <code className="le-mono">test-quality.json</code>.
              </p>
            ) : null}

            {ds.data?.feature_enabled === false ? (
              <p className="forge-support" style={{ marginTop: '0.75rem' }}>
                DevSecOps API disabled on server.
              </p>
            ) : ds.data?.provider_kind === 'local_fixture' && ds.data?.security_summary ? (
              <div style={{ marginTop: '1rem' }}>
                <h3 className="le-panel__title" style={{ fontSize: '1rem', marginBottom: '0.35rem' }}>
                  Security &amp; compliance (computed risk)
                </h3>
                <p className="forge-support" style={{ marginTop: 0 }}>
                  Risk score is derived from open findings, vulns, secrets, and dependency rows, minus control
                  mitigation and active exceptions — not a static badge.
                </p>
                <div className="le-stats">
                  <div className="le-stat">
                    <span className="le-stat__value">{ds.data.security_summary?.risk_score?.value ?? '—'}</span>
                    <span className="le-stat__label">Risk score</span>
                  </div>
                  <div className="le-stat">
                    <span className="le-stat__value">
                      {ds.data.security_summary?.security_release_gate?.passed === true
                        ? 'Pass'
                        : ds.data.security_summary?.security_release_gate?.passed === false
                          ? 'Fail'
                          : '—'}
                    </span>
                    <span className="le-stat__label">Sec gate</span>
                  </div>
                  <div className="le-stat">
                    <span className="le-stat__value">
                      {ds.data.security_summary?.rollup_repo?.open_security_findings ?? '—'}
                    </span>
                    <span className="le-stat__label">Open findings</span>
                  </div>
                </div>
                {ds.data.security_summary?.security_release_gate?.summary ? (
                  <p className="forge-support" style={{ marginBottom: 0 }}>
                    {ds.data.security_summary.security_release_gate.summary}
                  </p>
                ) : null}
                <p style={{ marginTop: '0.5rem', marginBottom: 0 }}>
                  <Link className="le-btn le-btn--small" to="/plan?tab=today#le-devsecops-h">
                    Open DevSecOps card
                  </Link>
                </p>
                <TechnicalDetails summary="DevSecOps API payload (inspect)" defaultOpen={false}>
                  <a className="le-btn le-btn--small" href={`/api/project/${enc}/devsecops`}>
                    Open raw JSON
                  </a>
                </TechnicalDetails>
              </div>
            ) : ds.phase === 'loading' && !ds.data ? (
              <p className="forge-support" style={{ marginTop: '0.75rem' }}>
                Loading security summary…
              </p>
            ) : ds.data?.provider_kind === 'scan_only' ? (
              <p className="forge-support" style={{ marginTop: '0.75rem' }}>
                No devsecops fixture — set <code className="le-mono">LENSES_DEVSECOPS_COMPLIANCE_SEED_DEMO=1</code>.
              </p>
            ) : null}
          </>
        ) : null}
      </section>

      {statsPayload ? (
        <>
          {contrib.length > 0 ? (
            <section className="le-panel">
              <h2 className="le-panel__title">Top contributors</h2>
              <div className="le-table-wrap">
                <table className="le-table">
                  <thead>
                    <tr>
                      <th>Commits</th>
                      <th>Author</th>
                    </tr>
                  </thead>
                  <tbody>
                    {contrib.slice(0, 12).map((r, i) => (
                      <tr key={`${r.name}-${i}`}>
                        <td>{r.commits}</td>
                        <td>{r.name}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          ) : (
            <StatePanel
              variant="empty"
              density="compact"
              title="No contributor roll-up"
              description="Git may have no recorded authors in the window, or this repo has no commits yet."
            />
          )}

          {exts.length > 0 ? (
            <section className="le-panel">
              <h2 className="le-panel__title">File extensions</h2>
              <div className="le-table-wrap">
                <table className="le-table">
                  <thead>
                    <tr>
                      <th>Extension</th>
                      <th>Files</th>
                    </tr>
                  </thead>
                  <tbody>
                    {exts.slice(0, 15).map((r) => (
                      <tr key={r.extension}>
                        <td className="le-mono">{r.extension}</td>
                        <td>{r.count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          ) : (
            <StatePanel
              variant="empty"
              density="compact"
              title="No extension breakdown"
              description="Extension stats were empty for this snapshot."
            />
          )}
        </>
      ) : null}

      <TechnicalDetails summary="Traceability (demo, inspect)" defaultOpen={false}>
        <div className="forge-support" style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'center' }}>
          <TraceabilityLaunchButton
            rootId={demoRepoEntityId(decoded)}
            label="Trace repo (demo)"
            title="If this child matches the seeded demo repo id, opens graph from repo node; otherwise use Trace sample story from Home or Plan"
          />
          <TraceabilityLaunchButton
            rootId={DEMO_ORCHESTRATION_STORY_ID}
            label="Trace sample story"
            title="End-to-end demo: story S-1842 through PR, build, release, evidence"
          />
        </div>
      </TechnicalDetails>

      <TechnicalDetails summary="Sample orchestration trace (demo, inspect)" defaultOpen={false}>
        <HandoffLoopPanel workItemId={DEMO_ORCHESTRATION_STORY_ID} traceQueryStoryId={DEMO_ORCHESTRATION_STORY_ID} />
        <OutcomeLoopPanel workItemId={DEMO_ORCHESTRATION_STORY_ID} traceQueryStoryId={DEMO_ORCHESTRATION_STORY_ID} />
      </TechnicalDetails>

      <TechnicalDetails summary="Raw API JSON (debug)" defaultOpen={false}>
        <pre className="le-preview le-json" style={{ maxHeight: '14rem' }}>
          {JSON.stringify(
            {
              context: ctxPayload,
              stats: statsPayload,
              repo_workflow: rw.data,
              quality: pq.data,
              devsecops: ds.data,
              phases: {
                stats: stats.phase,
                context: ctx.phase,
                repo_workflow: rw.phase,
                quality: pq.phase,
                devsecops: ds.phase,
              },
            },
            null,
            2,
          )}
        </pre>
      </TechnicalDetails>
    </>
  )
}
