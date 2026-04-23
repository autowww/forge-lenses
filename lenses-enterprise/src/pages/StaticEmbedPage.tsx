import { useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'
import { EmbeddedPreviewFrame } from '../components/EmbeddedPreviewFrame'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'
import { PageHeader, StatePanel } from '../components/page'
import { KNOWLEDGE_PUBLISH_COPILOT, STUDIO_IA, STUDIO_VIEWER } from '../nav/studioVisibleCopy'

type Kind = 'docs' | 'local-site'

function iframeSrcFor(kind: Kind, splat: string): string {
  const s = (splat || '').replace(/^\/+/, '')
  if (kind === 'docs') {
    return s ? `/docs/${s}` : '/docs/index.html'
  }
  return s ? `/local-site/${s}` : ''
}

export function StaticEmbedPage({ kind }: { kind: Kind }) {
  const params = useParams()
  const splat = (params['*'] ?? '').trim()

  useLensesCopilotPage({
    route: 'knowledge',
    defaultQuery: kind === 'docs' ? KNOWLEDGE_PUBLISH_COPILOT.lensesReference : undefined,
  })

  const iframeSrc = useMemo(() => iframeSrcFor(kind, splat), [kind, splat])

  const title =
    kind === 'docs'
      ? splat
        ? `Reference · ${splat}`
        : 'Lenses reference'
      : splat
        ? `Preview · ${splat}`
        : 'Site preview'

  if (kind === 'local-site' && !splat) {
    return (
      <>
        <PageHeader
          title="Site preview"
          subtitle="Static /local-site preview in Studio—add a folder path after /view/local-site/."
        />
        <StatePanel
          variant="invalid"
          title="Missing site path"
          description={
            <>
              Add the site folder after <code>/studio/view/local-site/</code> (for example <code>my-site/</code>).
              From Websites, use “Static preview in Studio” on a card, or pick a site and prefer the embedded
              legacy preview when you need full-workspace Sites chrome.
            </>
          }
          actions={
            <>
              <Link className="le-btn le-btn--primary" to="/websites">
                Websites
              </Link>
              <Link className="le-btn" to="/tutorials">
                Tutorials
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
        title={title}
        purpose={kind === 'docs' ? STUDIO_IA.lensesReferencePurposeLearn : undefined}
        subtitle={
          kind === 'docs' ? (
            <>
              {STUDIO_IA.lensesReferenceReadingSubtitle}{' '}
              <span className="le-shortcut-pill" title="Handbooks and guides use Tutorials">
                Reference
              </span>
            </>
          ) : (
            <>
              {STUDIO_VIEWER.localSitePathPageSubtitle}{' '}
              <span className="le-shortcut-pill" title="Built files only—no legacy Sites sidebar">
                Static preview
              </span>
            </>
          )
        }
      />
      <EmbeddedPreviewFrame
        title={title}
        src={iframeSrc}
        disclosureKind={kind === 'docs' ? 'reference-docs' : 'local-site-static'}
        toolbarBefore={
          <>
            <Link className="le-btn" to="/">
              Overview
            </Link>
            <Link className="le-btn" to="/view/docs">
              Lenses reference
            </Link>
            <Link className="le-btn" to="/websites">
              Sites
            </Link>
            <a className="le-btn" href={iframeSrc} target="_blank" rel="noreferrer">
              Open without shell
            </a>
          </>
        }
      />
    </>
  )
}
