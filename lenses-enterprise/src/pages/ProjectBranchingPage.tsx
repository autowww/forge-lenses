import { useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useResilientJsonBlock } from '../hooks/useResilientJsonBlock'
import { PageHeader, StatePanel, TechnicalDetails } from '../components/page'
import { ProjectLocalNav } from '../components/projects'
import { STUDIO_VOCAB } from '../nav/studioVisibleCopy'

type BranchingPayload = {
  ok?: boolean
  project?: string
  policy?: {
    source?: string
    trunk?: string
    model?: string
    team_scale?: string
    topology?: string
    cicd_maturity?: string
    require_pr?: boolean
    required_approvals?: number
    require_green_checks?: boolean
    lanes_enabled?: boolean
  }
  current?: {
    branch?: string
    head_short?: string
    origin_url?: string
    is_git?: boolean
  }
  structure?: {
    branches?: { name?: string; category?: string; protected?: boolean }[]
    branches_by_lane?: Record<string, { name?: string }[]>
    pull_requests?: { number?: number; title?: string; head_ref?: string; base_ref?: string; state?: string; mergeable?: string }[]
    branch_protection?: { pattern?: string; required_reviews?: number }[]
  }
  recommendations?: Record<string, string>
  hints?: string[]
}

export function ProjectBranchingPage() {
  const { name = '' } = useParams()
  const decoded = decodeURIComponent(name)
  const enc = encodeURIComponent(decoded)
  const apiUrl = decoded ? `/api/project/${enc}/branching` : null
  const data = useResilientJsonBlock<BranchingPayload>(apiUrl, {
    snapshotKey: `project-branching:${decoded}`,
  })

  if (!decoded) {
    return (
      <StatePanel
        variant="invalid"
        title="Missing project name"
        description="Use a URL like /studio/projects/my-repo/branching, or pick a repository from the projects list."
        actions={<Link to="/projects">All projects</Link>}
      />
    )
  }

  const payload = data.data
  const laneBuckets = payload?.structure?.branches_by_lane ?? {}
  const laneRows = useMemo(
    () =>
      Object.entries(laneBuckets)
        .map(([lane, rows]) => ({ lane, count: Array.isArray(rows) ? rows.length : 0 }))
        .filter((row) => row.count > 0)
        .sort((a, b) => b.count - a.count),
    [laneBuckets],
  )
  const prs = payload?.structure?.pull_requests ?? []
  const branchProtection = payload?.structure?.branch_protection ?? []
  const recommendations = payload?.recommendations ?? {}

  return (
    <>
      <PageHeader
        title={`${decoded} · ${STUDIO_VOCAB.projectBranching}`}
        preface={
          <Link to={`/projects/${enc}`} className="forge-support">
            ← {STUDIO_VOCAB.projectDashboard}
          </Link>
        }
        subtitle="Review branch strategy policy, current branch structure, and Branch Steward guidance for this repository."
      />
      <ProjectLocalNav projectName={decoded} />

      {data.phase === 'stale' && (
        <StatePanel variant="stale" title="Showing saved branching snapshot" description="Live refresh did not complete; rendered from the most recent successful payload in this browser." />
      )}
      {data.phase === 'error' && payload && (
        <StatePanel variant="unavailable" title="Live branching refresh failed" description="Showing cached branching data from an earlier successful load." />
      )}

      {data.phase === 'loading' && !payload && (
        <StatePanel variant="loading" title="Loading branching strategy" description="Resolving policy and branch structure…" />
      )}
      {data.phase === 'error' && !payload && (
        <StatePanel
          variant="error"
          title="Branching strategy unavailable"
          description="Could not load project branching information."
          actions={<button onClick={() => data.retry()}>Retry</button>}
        />
      )}

      {payload && (
        <>
          <section>
            <h2>Strategy</h2>
            <ul>
              <li>Policy source: <code>{payload.policy?.source || 'unknown'}</code></li>
              <li>Model: <code>{payload.policy?.model || 'team_tier'}</code></li>
              <li>Trunk: <code>{payload.policy?.trunk || 'main'}</code></li>
              <li>
                Team profile: <code>{payload.policy?.team_scale || 'unknown'}</code> · <code>{payload.policy?.topology || 'unknown'}</code> ·{' '}
                <code>{payload.policy?.cicd_maturity || 'unknown'}</code>
              </li>
              <li>
                Merge guardrails: PR <code>{String(Boolean(payload.policy?.require_pr))}</code>, approvals{' '}
                <code>{String(payload.policy?.required_approvals ?? 0)}</code>, green checks{' '}
                <code>{String(Boolean(payload.policy?.require_green_checks))}</code>
              </li>
              <li>
                Current branch: <code>{payload.current?.branch || 'n/a'}</code> @{payload.current?.head_short || 'n/a'}
              </li>
            </ul>
          </section>

          <section>
            <h2>Structure</h2>
            <ul>
              {laneRows.length ? laneRows.map((row) => <li key={row.lane}><code>{row.lane}</code>: {row.count} branch(es)</li>) : <li>No lane-grouped branches in current payload.</li>}
            </ul>
            <p>Open PRs: <strong>{prs.length}</strong></p>
            <p>Branch protection rules: <strong>{branchProtection.length}</strong></p>
          </section>

          <section>
            <h2>Agent Guidance</h2>
            <ul>
              {Object.entries(recommendations).map(([key, value]) => (
                <li key={key}>
                  <code>{key}</code>: {value}
                </li>
              ))}
            </ul>
          </section>

          <TechnicalDetails summary="Branching payload details">
            <pre>{JSON.stringify(payload, null, 2)}</pre>
          </TechnicalDetails>
        </>
      )}
    </>
  )
}
