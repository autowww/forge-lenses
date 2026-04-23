import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiGetJson } from '../api/http'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'
import { PageHeader, StatePanel, TechnicalDetails } from '../components/page'
import { embedUrlForStaticPath } from '../util/staticPreviewUrl'
import { KNOWLEDGE_PUBLISH_COPILOT, ROUTE_SUBTITLE, STUDIO_IA, STUDIO_VOCAB } from '../nav/studioVisibleCopy'

type Row = {
  child_name: string
  kind: string
  label: string
  preview_url: string
}

export function TutorialsPage() {
  useLensesCopilotPage({ route: 'knowledge', defaultQuery: KNOWLEDGE_PUBLISH_COPILOT.tutorialsHub })
  const [rows, setRows] = useState<Row[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    void (async () => {
      await Promise.resolve()
      setLoading(true)
      try {
        const r = await apiGetJson<{ ok?: boolean; rows?: Row[] }>('/api/tutorials-index')
        setRows(r.rows ?? [])
      } catch {
        setRows([])
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  return (
    <>
      <PageHeader
        title="Tutorials & handbooks"
        purpose={STUDIO_IA.tutorialsPagePurposeLearn}
        subtitle={ROUTE_SUBTITLE.tutorialsReference}
        statusChips={[{ label: 'Learn', tone: 'muted' }]}
        secondaryMenuItems={[
          { key: 'docs', label: STUDIO_VOCAB.lensesReference, to: '/view/docs/' },
          { key: 'notes', label: STUDIO_VOCAB.workspaceNotes, to: '/workspace-md' },
          { key: 'search', label: STUDIO_VOCAB.search, to: '/search' },
        ]}
      />
      <TechnicalDetails summary="Technical — tutorials index endpoint" defaultOpen={false}>
        <p className="forge-support">
          <code className="le-mono">GET /api/tutorials-index</code> — same discovery as the full workspace{' '}
          <code>/tutorials</code> list.
        </p>
      </TechnicalDetails>
      {loading ? (
        <StatePanel variant="loading" title="Loading handbooks" description="Reading the tutorials index from your workspace." />
      ) : null}
      <ul className="le-list" style={{ listStyle: 'none', paddingLeft: 0 }}>
        {rows.map((r, i) => (
          <li key={`${r.child_name}-${r.kind}-${i}`} className="le-card" style={{ marginBottom: '0.5rem' }}>
            <strong>{r.child_name}</strong> — {r.label}{' '}
            <span className="le-muted">({r.kind})</span>
            <div>
              <Link to={embedUrlForStaticPath(r.preview_url)}>Open preview</Link>
            </div>
          </li>
        ))}
      </ul>
      {!loading && rows.length === 0 ? (
        <StatePanel
          variant="empty"
          title="No handbooks detected in this workspace"
          description="This list fills when the scan finds tutorial sources. For markdown logs and proof in your repo, open Workspace notes; for methodology-linked proof, use the Evidence registry under Govern."
          actions={
            <>
              <Link className="le-btn le-btn--primary" to="/workspace-md">
                Workspace notes
              </Link>
              <Link className="le-btn" to="/knowledge/methodology/evidence">
                Evidence registry
              </Link>
              <Link className="le-btn" to="/plan">
                Plan summary
              </Link>
            </>
          }
        />
      ) : null}

    </>
  )
}
