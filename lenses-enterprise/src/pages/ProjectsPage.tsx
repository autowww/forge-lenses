import { useMemo } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import type { WorkspaceChild } from '../api/workspace'
import { WorkspaceStateFallback } from '../components/WorkspaceStateFallback'
import { StatePanel } from '../components/page'
import { useWorkspace } from '../context/WorkspaceContext'
import { useNavigationMode } from '../nav/useNavigationMode'
import { ProjectsArtifactsPortfolio } from '../components/projects'
import { PROJECT_OBJECT_HOME } from '../nav/studioVisibleCopy'
import { filterPortfolioRows, parsePortfolioTableFilter } from '../lib/portfolioDrilldown'
import { buildRepoPortfolioRows } from '../lib/workspacePortfolio'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'

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
        {visibleGit.map((c) => (
          <div key={c.name} className="le-card">
            <h3>{c.name}</h3>
            <p className="forge-support">{c.is_git ? 'Git repository' : 'Folder'}</p>
            <Link to={`/projects/${encodeURIComponent(c.name)}`}>Dashboard →</Link>
          </div>
        ))}
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
  useLensesCopilotPage({ route: 'projects' })
  const { mode } = useNavigationMode()
  const { state, loading, error, errorDescription, errorDetail } = useWorkspace()

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
