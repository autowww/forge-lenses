import { useEffect, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useWorkspace } from '../../context/WorkspaceContext'
import { useResilientJsonBlock } from '../../hooks/useResilientJsonBlock'
import { StatePanel } from '../page/StatePanel'
import { recordPageFailure } from '../../telemetry/studioTelemetry'

type Health = {
  open_prs_count?: number
  stale_open_prs_count?: number
  blocked_merge_count?: number
  review_debt_total?: number
  unlinked_work_items_count?: number
}

type RepoRow = {
  project: string
  provider?: string
  health?: Health
  work_item_links?: { story_id?: string }[]
  data_sources?: string[]
}

export type RepoWorkflowOverviewPayload = {
  ok?: boolean
  feature_enabled?: boolean
  provider_kind?: string
  repos?: RepoRow[]
  hints?: string[]
  resolved_at?: string
}

/**
 * Plan → Today: PR/MR health, review debt, and unlinked work — from normalized repo-workflow fixtures
 * (GitHub / GitLab / Azure Repos adapters; local JSON + demo seed).
 */
export function RepoWorkflowOpsCard() {
  const { state } = useWorkspace()
  const refreshKey = state?.resolved_at ?? null

  const block = useResilientJsonBlock<RepoWorkflowOverviewPayload>('/api/repo-workflow/overview', {
    snapshotKey: 'repo-workflow-overview',
    refreshKey,
  })

  const data = block.data
  const phase = block.phase

  useEffect(() => {
    if (phase === 'error' && block.failure) {
      recordPageFailure('repo_workflow_overview', block.failure.summary)
    }
  }, [phase, block.failure])

  let inner: ReactNode

  if (phase === 'loading' && !data) {
    inner = (
      <StatePanel
        variant="loading"
        density="compact"
        title="Loading code workflow overlay"
        description="Branches, pull requests, merge readiness, and planning links from repo-workflow fixtures."
      />
    )
  } else if (phase === 'error' && !data) {
    inner = (
      <StatePanel
        variant="error"
        density="compact"
        title="Could not load repo workflow overview"
        description="Confirm the Lenses server is running, then retry."
        technicalDetail={block.failure?.summary ?? null}
        actions={
          <button type="button" className="le-btn le-btn--primary" onClick={() => block.retry()}>
            Retry
          </button>
        }
      />
    )
  } else if (!data?.ok) {
    inner = (
      <StatePanel variant="empty" density="compact" title="Repo workflow unavailable" description="Unexpected payload." />
    )
  } else if (data.feature_enabled === false) {
    inner = (
      <StatePanel
        variant="empty"
        density="compact"
        title="Code workflow overlay disabled"
        description={
          <>
            Set <code className="le-mono">LENSES_EXPERIMENTAL_REPO_WORKFLOW=1</code> (default) and restart Lenses
            to enable PR/MR health widgets.
          </>
        }
      />
    )
  } else {
    const repos = data.repos ?? []
    const fixture = data.provider_kind === 'local_fixture'

    inner = (
      <>
        {!fixture ? (
          <StatePanel
            variant="empty"
            density="compact"
            title="No repo-workflow fixture"
            description={
              <>
                Add <code className="le-mono">.lenses-local/repo-workflow.json</code> or{' '}
                <code className="le-mono">LENSES_REPO_WORKFLOW_SEED_DEMO=1</code> for normalized PR/MR rows.
              </>
            }
          />
        ) : null}
        {data.hints?.length ? (
          <ul className="forge-support" style={{ marginBottom: '0.75rem' }}>
            {data.hints.map((h) => (
              <li key={h.slice(0, 96)}>{h}</li>
            ))}
          </ul>
        ) : null}
        {repos.length === 0 ? (
          <p className="le-delivery-section__empty">No repositories in the workspace scan.</p>
        ) : (
          <div className="le-cc-table-wrap" style={{ overflowX: 'auto' }}>
            <table className="le-cc-table">
              <caption className="forge-support" style={{ textAlign: 'left', marginBottom: '0.35rem' }}>
                Code workflow and merge readiness
              </caption>
              <thead>
                <tr>
                  <th scope="col">Repository</th>
                  <th scope="col">VCS</th>
                  <th scope="col">Open PRs</th>
                  <th scope="col">Stale</th>
                  <th scope="col">Blocked merge</th>
                  <th scope="col">Review debt</th>
                  <th scope="col">Unlinked items</th>
                </tr>
              </thead>
              <tbody>
                {repos.map((r) => {
                  const enc = encodeURIComponent(r.project)
                  const h = r.health ?? {}
                  return (
                    <tr key={r.project}>
                      <td>
                        <Link to={`/projects/${enc}`}>{r.project}</Link>
                      </td>
                      <td>{r.provider || <span className="forge-support">—</span>}</td>
                      <td>{h.open_prs_count ?? 0}</td>
                      <td>{h.stale_open_prs_count ?? 0}</td>
                      <td>{h.blocked_merge_count ?? 0}</td>
                      <td>{h.review_debt_total ?? 0}</td>
                      <td>{h.unlinked_work_items_count ?? '—'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
        <p className="forge-support" style={{ marginTop: '0.5rem' }}>
          Provider: <code className="le-mono">{data.provider_kind ?? 'unknown'}</code>
          {data.resolved_at ? (
            <>
              {' '}
              · Scan <time dateTime={data.resolved_at}>{data.resolved_at}</time>
            </>
          ) : null}
        </p>
      </>
    )
  }

  return (
    <section className="le-delivery-section" aria-labelledby="le-repo-workflow-h">
      <h2 id="le-repo-workflow-h" className="le-delivery-section__title">
        Code workflow and PR health
      </h2>
      <p className="le-delivery-section__lead">
        Normalized views across GitHub, GitLab, and Azure Repos: open and stale PRs/MRs, blocked merges, review
        debt, and story-to-branch links. Data is local-first (
        <code className="le-mono">repo-workflow.json</code>); remote adapters implement the same contract.
      </p>
      {inner}
    </section>
  )
}
