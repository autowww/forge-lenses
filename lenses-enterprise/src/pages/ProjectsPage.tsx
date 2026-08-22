import { useMemo } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import type { WorkspaceChild } from '../api/workspace'
import { ExecutiveSummaryStrip } from '../components/shell/ExecutiveSummaryStrip'
import { WorkspaceStateFallback } from '../components/WorkspaceStateFallback'
import { StatePanel } from '../components/page'
import { useWorkspace } from '../context/WorkspaceContext'
import { useNavigationMode } from '../nav/useNavigationMode'
import { ProjectsArtifactsPortfolio } from '../components/projects'
import { PROJECT_OBJECT_HOME, PROJECT_PORTFOLIO_COPILOT_DEFAULT } from '../nav/studioVisibleCopy'
import { filterPortfolioRows, parsePortfolioTableFilter } from '../lib/portfolioDrilldown'
import { buildRepoPortfolioRows } from '../lib/workspacePortfolio'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'
import { chargeMdCandidates } from '../lib/copilotPageEvidence'
import { WorkspaceSparseGuide } from '../components/onboarding/WorkspaceSparseGuide'

function sortFlowCards(children: WorkspaceChild[]) {
  const list = [...children]
  return list.sort((a, b) => {
    const an = String(a.name || '')
    const bn = String(b.name || '')
    const aNoise = an === '__pycache__' || an === 'node_modules'
    const bNoise = bn === '__pycache__' || bn === 'node_modules'
    if (aNoise !== bNoise) return aNoise ? 1 : -1
    const ag = a.is_git ? 1 : 0
    const bg = b.is_git ? 1 : 0
    if (ag !== bg) return bg - ag
    return an.localeCompare(bn, undefined, { sensitivity: 'base' })
  })
}

function healthTierLabel(health: 'healthy' | 'watch' | 'at_risk'): string {
  if (health === 'at_risk') return 'At risk'
  if (health === 'watch') return 'Watch'
  return 'Ready'
}

function ProjectsFlowCardGrid() {
  const { state } = useWorkspace()
  const [sp] = useSearchParams()
  const filter = parsePortfolioTableFilter(sp.get('filter'))
  const portfolioRows = useMemo(
    () => (state ? buildRepoPortfolioRows(state, null) : []),
    [state],
  )
  const allowedGit = useMemo(() => {
    if (!state || filter === 'all') return null
    const names = new Set(filterPortfolioRows(portfolioRows, filter).map((r) => r.name))
    return names
  }, [state, portfolioRows, filter])

  if (!state) return <WorkspaceStateFallback />
  const children = sortFlowCards(Array.isArray(state.children) ? state.children : [])

  const gitCards = children.filter((c) => c.is_git)
  const folderCards = children.filter((c) => !c.is_git)
  const visibleGit =
    allowedGit == null ? gitCards : gitCards.filter((c) => allowedGit.has(String(c.name ?? '')))

  return (
    <>
      <ExecutiveSummaryStrip />
      <WorkspaceSparseGuide telemetryTag="projects" lead="Add more git repositories to your workspace root to populate this portfolio grid." />
      <h1 className="le-h1">Projects</h1>
      <p className="forge-support" style={{ marginTop: '-0.35rem', marginBottom: '1rem', maxWidth: '44rem' }}>
        {PROJECT_OBJECT_HOME.listVersusDashboardLead}
      </p>
      {filter !== 'all' ? (
        <p className="forge-support" style={{ marginBottom: '0.75rem' }}>
          Filter <strong>{filter}</strong> (from workspace health signals).{' '}
          <Link to="/projects">Show all repositories</Link>
          {' · '}
          <Link to="/projects?filter=attention">Attention</Link>
          {' · '}
          <Link to="/projects?filter=dirty">Dirty</Link>
          {' · '}
          <Link to="/projects?filter=evidence">Evidence</Link>
        </p>
      ) : null}
      {filter !== 'all' && visibleGit.length === 0 ? (
        <StatePanel
          variant="empty"
          density="compact"
          title="No repositories match this filter"
          description="Try another filter or clear to see every git root. For the full sortable table, switch to the Artifacts lens."
          actions={
            <>
              <Link className="le-btn le-btn--primary le-btn--small" to="/projects">
                Clear filter
              </Link>
              <Link className="le-btn le-btn--small" to="/">
                Workspace overview
              </Link>
            </>
          }
        />
      ) : null}
      <div className="le-card-grid">
        {visibleGit.map((c) => {
          const row = portfolioRows.find((r) => r.name === c.name)
          const healthTier = row ? healthTierLabel(row.health) : 'Ready'
          return (
            <div key={c.name} className="le-card">
              <h3>{c.name}</h3>
              <p className="forge-support">
                Git repository
                <span className="le-health-tier" style={{ marginLeft: '0.5rem' }}>
                  · {healthTier}
                </span>
              </p>
              <Link to={`/projects/${encodeURIComponent(c.name)}`}>Dashboard →</Link>
            </div>
          )
        })}
        {filter === 'all'
          ? folderCards.map((c) => (
              <div key={c.name} className="le-card">
                <h3>{c.name}</h3>
                <p className="forge-support">Folder</p>
                <Link to={`/projects/${encodeURIComponent(c.name)}`}>Open →</Link>
              </div>
            ))
          : null}
      </div>
      {filter !== 'all' && folderCards.length > 0 ? (
        <>
          <h2 className="le-h1" style={{ fontSize: '1rem', marginTop: '1.25rem' }}>
            Other workspace folders
          </h2>
          <p className="forge-support">Filters apply to git repositories; folders are listed for context.</p>
          <div className="le-card-grid">
            {folderCards.map((c) => (
              <div key={c.name} className="le-card">
                <h3>{c.name}</h3>
                <p className="forge-support">Folder</p>
                <Link to={`/projects/${encodeURIComponent(c.name)}`}>Open →</Link>
              </div>
            ))}
          </div>
        </>
      ) : null}
    </>
  )
}

export function ProjectsPage() {
  const { mode } = useNavigationMode()
  const { state, loading, error, errorDescription, errorDetail } = useWorkspace()
  const copilotScope = useMemo(() => {
    const children = Array.isArray(state?.children) ? state.children : []
    const gitN = children.filter((c) => c.is_git).length
    const folderN = children.length - gitN
    return {
      pageContextSummary:
        `Forge Studio · Projects · workspace portfolio (${gitN} git repos, ${folderN} folders, ${children.length} entries). ` +
        'When asked for one-line summaries, cover each repository/folder from the workspace roster citation; cite sources and note gaps.',
      relatedMdRelPaths: chargeMdCandidates(undefined),
    }
  }, [state?.children, state?.resolved_at])
  useLensesCopilotPage({
    route: 'projects',
    pageContextSummary: copilotScope.pageContextSummary,
    relatedMdRelPaths: copilotScope.relatedMdRelPaths,
    defaultQuery: PROJECT_PORTFOLIO_COPILOT_DEFAULT,
  })

  if (loading && !state) {
    return (
      <StatePanel
        variant="loading"
        title="Loading projects"
        description="Gathering repositories and folders from your latest workspace scan."
      />
    )
  }
  if (error) {
    return (
      <StatePanel
        variant="error"
        title={error}
        description={
          errorDescription ||
          'Projects need a successful workspace scan. Confirm Lenses is running and this machine can reach it, then try again.'
        }
        technicalDetail={errorDetail}
        aiRecovery={{
          prompt: 'Projects in Lenses did not load. How do I reconnect the workspace or fix the scan?',
          label: 'Ask Chat about workspace setup',
        }}
        actions={
          <button type="button" className="le-btn le-btn--primary" onClick={() => window.location.reload()}>
            Reload page
          </button>
        }
      />
    )
  }
  if (!state) {
    return null
  }

  if (mode === 'artifacts') {
    return <ProjectsArtifactsPortfolio />
  }

  return <ProjectsFlowCardGrid />
}
