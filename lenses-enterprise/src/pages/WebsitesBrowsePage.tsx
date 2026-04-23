import { Link, useParams } from 'react-router-dom'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'
import { EmbeddedPreviewFrame } from '../components/EmbeddedPreviewFrame'
import { ObjectMetaBar, PageHeader, StatePanel } from '../components/page'
import { useWorkspace } from '../context/WorkspaceContext'
import { KNOWLEDGE_PUBLISH_COPILOT, STUDIO_VIEWER, STUDIO_VOCAB as V } from '../nav/studioVisibleCopy'

/** iframe to full-workspace Sites browse + preview (same origin). */
export function WebsitesBrowsePage() {
  const { site = '' } = useParams()
  const decoded = decodeURIComponent(site)
  const src = `/websites/browse?site=${encodeURIComponent(decoded)}`
  const { state, loading, error, errorDescription, errorDetail } = useWorkspace()

  useLensesCopilotPage({ route: 'publish', defaultQuery: KNOWLEDGE_PUBLISH_COPILOT.publishWebsites })

  if (loading && !state) {
    return (
      <>
        <PageHeader
          title={V.siteBrowse}
          subtitle={STUDIO_VIEWER.siteBrowsePageSubtitle}
        />
        <StatePanel
          variant="loading"
          title="Loading workspace scan"
          description="Checking published site names from the latest scan before opening the embedded preview."
        />
      </>
    )
  }

  if (error) {
    return (
      <>
        <PageHeader
          title={V.siteBrowse}
          subtitle={STUDIO_VIEWER.siteBrowsePageSubtitle}
        />
        <StatePanel
          variant="error"
          title={error}
          description={
            errorDescription ||
            'Without the workspace scan we can’t validate site names or open the preview safely.'
          }
          technicalDetail={errorDetail}
          actions={
            <button type="button" className="le-btn le-btn--primary" onClick={() => window.location.reload()}>
              Reload page
            </button>
          }
        />
      </>
    )
  }

  if (!decoded.trim()) {
    return (
      <>
        <PageHeader title={V.siteBrowse} subtitle={STUDIO_VIEWER.siteBrowsePageSubtitle} />
        <StatePanel
          variant="invalid"
          title="No site in the URL"
          description="Pick a published site from the Websites list so the path includes its folder name (for example /studio/websites/browse/my-site)."
          actions={
            <Link className="le-btn le-btn--primary" to="/websites">
              {V.websites}
            </Link>
          }
        />
      </>
    )
  }

  const knownNames = new Set((state?.websites ?? []).map((w) => w.name))
  const isKnown = knownNames.size === 0 || knownNames.has(decoded)

  if (state && !isKnown) {
    return (
      <>
        <PageHeader
          title={STUDIO_VIEWER.unknownSitePageTitle(decoded)}
          subtitle={STUDIO_VIEWER.unknownSitePageSubtitle}
        />
        <StatePanel
          variant="invalid"
          title="Site not in this workspace scan"
          description="The URL may be stale, the folder may live under another workspace root, or you may need a rescan after adding Firebase or static output."
          technicalDetail={`Requested folder: ${decoded}`}
          actions={
            <>
              <Link className="le-btn le-btn--primary" to="/websites">
                View scanned sites
              </Link>
              <Link className="le-btn" to="/">
                Workspace overview
              </Link>
            </>
          }
        />
      </>
    )
  }

  return (
    <>
      <PageHeader
        title={`${V.siteBrowse} · ${decoded}`}
        purpose={STUDIO_VIEWER.siteBrowsePreviewPurpose}
        subtitle={STUDIO_VIEWER.siteBrowsePageSubtitle}
        secondaryMenuItems={[
          { key: 'websites', label: V.websites, to: '/websites' },
          { key: 'today', label: V.today, to: '/plan?tab=today' },
          { key: 'blog', label: V.blog, to: '/blog' },
        ]}
      />
      <ObjectMetaBar
        label="Published site"
        items={[{ label: STUDIO_VIEWER.metaPublishedSiteFolder, value: decoded }]}
      />
      <EmbeddedPreviewFrame
        title={`${V.siteBrowse} — ${decoded}`}
        src={src}
        frameMinHeight="min(80vh, 40rem)"
        disclosureKind="workspace-legacy-sites"
      />
    </>
  )
}
