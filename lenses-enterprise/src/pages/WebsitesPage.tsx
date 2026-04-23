import { Link } from 'react-router-dom'
import { SitesArtifactsHub } from '../components/sites'
import { StudioInlineAssist } from '../components/StudioInlineAssist'
import { WorkspaceStateFallback } from '../components/WorkspaceStateFallback'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'
import { PageHeader, StatePanel, TechnicalDetails } from '../components/page'
import { useWorkspace } from '../context/WorkspaceContext'
import { useNavigationMode } from '../nav/useNavigationMode'
import {
  FULL_WORKSPACE_UI,
  KNOWLEDGE_PUBLISH_COPILOT,
  STUDIO_VIEWER,
  STUDIO_VOCAB,
} from '../nav/studioVisibleCopy'

function WebsitesFlowView() {
  useLensesCopilotPage({ route: 'publish', defaultQuery: KNOWLEDGE_PUBLISH_COPILOT.publishWebsites })
  const { state } = useWorkspace()
  if (!state) return <WorkspaceStateFallback />
  const sites = state.websites ?? []

  return (
    <>
      <PageHeader
        title={STUDIO_VOCAB.websites}
        purpose={STUDIO_VIEWER.websitesIndexPurpose}
        subtitle={STUDIO_VIEWER.websitesIndexLead}
        statusChips={[{ label: `${sites.length} in scan`, tone: 'muted' }]}
        secondaryMenuItems={[
          { key: 'today', label: STUDIO_VOCAB.today, to: '/plan?tab=today' },
          { key: 'notes', label: STUDIO_VOCAB.workspaceNotes, to: '/workspace-md' },
          { key: 'blog', label: STUDIO_VOCAB.blog, to: '/blog' },
          { key: 'static', label: 'Static preview shell', to: '/view/local-site/' },
          { key: 'home', label: STUDIO_VOCAB.overview, to: '/' },
        ]}
      />
      <TechnicalDetails summary="Classic full-workspace websites list">
        <p className="forge-support">
          {FULL_WORKSPACE_UI.openFullWebsitesList}:{' '}
          <a href="/websites" target="_blank" rel="noreferrer">
            /websites
          </a>{' '}
          <span className="le-shortcut-pill">Legacy UI</span>
        </p>
      </TechnicalDetails>
      <StudioInlineAssist />
      <div className="le-card-grid">
        {sites.map((w) => (
          <div key={w.name} className="le-card">
            <h3>{w.name}</h3>
            <p className="forge-support">
              {w.html_total != null ? `${w.html_total} HTML pages` : ''}
            </p>
            <Link
              className="le-btn le-btn--primary"
              to={`/websites/browse/${encodeURIComponent(w.name)}`}
              title="Embeds legacy full-workspace Sites browse + preview"
            >
              {STUDIO_VIEWER.ctaEmbeddedSitesPreview}
            </Link>
            <div style={{ marginTop: '0.5rem' }}>
              <Link
                className="le-muted"
                to={`/view/local-site/${encodeURIComponent(w.name)}/`}
                title="Direct /local-site static tree in Studio—no legacy Sites chrome"
              >
                {STUDIO_VIEWER.ctaStaticPreviewInStudio}
              </Link>
            </div>
          </div>
        ))}
      </div>
      {sites.length === 0 ? (
        <StatePanel
          variant="empty"
          title="No published sites detected"
          description="Sites appear after a scan finds Firebase or static HTML roots. Until then, capture work in Plan and evidence in Workspace notes—when a site is built, rescan and return here to preview what ships."
          actions={
            <>
              <Link className="le-btn le-btn--primary" to="/plan?tab=today">
                {STUDIO_VOCAB.today}
              </Link>
              <Link className="le-btn" to="/workspace-md">
                {STUDIO_VOCAB.workspaceNotes}
              </Link>
              <Link className="le-btn" to="/">
                Workspace overview
              </Link>
            </>
          }
        />
      ) : null}

    </>
  )
}

export function WebsitesPage() {
  const { mode } = useNavigationMode()
  const { state, loading, error, errorDescription, errorDetail } = useWorkspace()

  if (loading && !state) {
    return (
      <StatePanel
        variant="loading"
        title="Loading websites"
        description="Reading the workspace scan for published static or Firebase sites."
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
          'We need a successful workspace scan to list published sites. Confirm Lenses is running, then retry.'
        }
        technicalDetail={errorDetail}
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
    return <SitesArtifactsHub />
  }

  return <WebsitesFlowView />
}
