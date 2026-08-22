import { useCallback, useEffect, useId, useState } from 'react'
import { Link } from 'react-router-dom'
import { getProjectDocsHealth, postProjectDocsHealth, type DocsHealthProjectPayload } from '../../api/docsHealth'
import { StatePanel } from '../page'
import { STUDIO_VOCAB } from '../../nav/studioVisibleCopy'

type Props = { projectName: string }

function formatWhen(iso: string | undefined) {
  if (!iso) return 'Not yet'
  try {
    return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
  } catch {
    return iso
  }
}

export function DocsHealthProjectCard({ projectName }: Props) {
  const titleId = useId()
  const [data, setData] = useState<DocsHealthProjectPayload | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [indexing, setIndexing] = useState(false)
  const [banner, setBanner] = useState<string | null>(null)
  const enc = encodeURIComponent(projectName)

  const load = useCallback(() => {
    void getProjectDocsHealth(projectName)
      .then((d) => {
        setData(d)
        setErr(null)
      })
      .catch(() => {
        setData(null)
        setErr('unavailable')
      })
  }, [projectName])

  useEffect(() => {
    load()
  }, [load])

  const runIndex = useCallback(async () => {
    setIndexing(true)
    setBanner(null)
    try {
      const out = await postProjectDocsHealth(projectName, { op: 'inventory' })
      if (out.ok) {
        setBanner('Documentation list updated.')
        load()
      } else {
        setBanner('Could not update the documentation list.')
      }
    } catch {
      setBanner('Something went wrong while indexing.')
    } finally {
      setIndexing(false)
    }
  }, [projectName, load])

  if (err) {
    return (
      <section className="le-panel" aria-labelledby={titleId}>
        <h2 id={titleId} className="le-panel__title">
          {STUDIO_VOCAB.docsHealth}
        </h2>
        <p className="forge-support">Documentation health is not available from this server or your account cannot read it.</p>
      </section>
    )
  }

  if (!data?.ok) {
    return (
      <StatePanel
        variant="loading"
        density="compact"
        title="Loading documentation overview"
        description="Fetching your documentation contract and file list."
      />
    )
  }

  const cs = data.contract_status
  const inv = data.inventory_summary
  const docCount = inv?.document_count ?? 0
  const reqTypes = data.required_doc_type_count ?? 0
  const contractLabel =
    cs?.mode === 'configured'
      ? 'Using your team documentation checklist file.'
      : 'Using sensible defaults until you add a checklist file in the repository.'
  const href = `/projects/${enc}/docs-health`
  const emptyDocs = docCount === 0 && !indexing

  return (
    <section className="le-panel" aria-labelledby={titleId}>
      <div className="le-panel__head">
        <h2 id={titleId} className="le-panel__title">
          {STUDIO_VOCAB.docsHealth}
        </h2>
        <Link className="le-btn le-btn--small le-btn--primary" to={href}>
          Open documentation health
        </Link>
      </div>
      <p className="forge-support">{contractLabel}</p>
      <ul className="le-muted" style={{ margin: '0.5rem 0', paddingLeft: '1.25rem' }} aria-label="Documentation counts">
        <li>
          Markdown pages found: <strong>{inv ? docCount : '—'}</strong>
        </li>
        <li>
          Documentation types we look for: <strong>{reqTypes}</strong>
        </li>
        <li>
          Last documentation list update: <strong>{formatWhen(inv?.updated_at)}</strong>
        </li>
      </ul>
      {emptyDocs ? (
        <p className="forge-support" role="status">
          No markdown pages were found in the usual folders yet. Add a README or docs folder, then update the list.
        </p>
      ) : null}
      {banner ? (
        <p className="forge-support" role="status">
          {banner}
        </p>
      ) : null}
      {(data.work_items?.length ?? 0) > 0 ? (
        <p className="le-muted" style={{ marginTop: '0.35rem' }}>
          {data.work_items!.length} follow-up item(s) — open <Link to="/plan?tab=today">Work → Today</Link>.
        </p>
      ) : null}
      {typeof data.open_tasklet_followups === 'number' && data.open_tasklet_followups > 0 ? (
        <p className="forge-support" role="status" style={{ marginTop: '0.35rem' }}>
          <strong>{data.open_tasklet_followups}</strong> documentation tasklet run(s) need attention (resume, input, or
          approval).{' '}
          <Link to={href}>Open documentation health</Link> to continue.
        </p>
      ) : null}
      {(data.tasklet_runs?.length ?? 0) > 0 ? (
        <ul className="le-muted" style={{ margin: '0.35rem 0 0', paddingLeft: '1.25rem', fontSize: '0.9rem' }}>
          {data.tasklet_runs!.slice(0, 4).map((tr) => (
            <li key={String(tr.id ?? tr.docs_health_session_id)}>
              Tasklet <code className="le-mono">{tr.state ?? '—'}</code>
              {tr.docs_health_session_id ? (
                <>
                  {' '}
                  ·{' '}
                  <Link
                    to={`/projects/${enc}/docs-health/session/${encodeURIComponent(String(tr.docs_health_session_id))}`}
                  >
                    session
                  </Link>
                </>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
      <div style={{ marginTop: '0.75rem', display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
        <button type="button" className="le-btn le-btn--primary" disabled={indexing} onClick={() => void runIndex()}>
          {indexing ? 'Updating list…' : 'Index documentation'}
        </button>
        <button
          type="button"
          className="le-btn"
          disabled
          aria-disabled="true"
          title="Full quality scan ships in the next sprint. Index first so scans have a fresh file list."
        >
          Run quality scan
        </button>
      </div>
    </section>
  )
}
