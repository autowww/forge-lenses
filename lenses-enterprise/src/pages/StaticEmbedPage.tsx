import { useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'
import { EmbeddedPreviewFrame } from '../components/EmbeddedPreviewFrame'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'
import { PageHeader } from '../components/page'
import { KNOWLEDGE_PUBLISH_COPILOT, STUDIO_IA } from '../nav/studioVisibleCopy'

function iframeSrcFor(splat: string): string {
  const s = (splat || '').replace(/^\/+/, '')
  return s ? `/docs/${s}` : '/docs/index.html'
}

export function StaticEmbedPage() {
  const params = useParams()
  const splat = (params['*'] ?? '').trim()

  useLensesCopilotPage({
    route: 'knowledge',
    defaultQuery: KNOWLEDGE_PUBLISH_COPILOT.lensesReference,
  })

  const iframeSrc = useMemo(() => iframeSrcFor(splat), [splat])

  const title = splat ? `Reference · ${splat}` : 'Lenses reference'

  return (
    <>
      <PageHeader
        title={title}
        purpose={STUDIO_IA.lensesReferencePurposeLearn}
        subtitle={
          <>
            {STUDIO_IA.lensesReferenceReadingSubtitle}{' '}
            <span className="le-shortcut-pill" title="Handbooks and guides use Tutorials">
              Reference
            </span>
          </>
        }
      />
      <EmbeddedPreviewFrame
        title={title}
        src={iframeSrc}
        disclosureKind="reference-docs"
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
