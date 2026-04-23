import { useCallback, useEffect, useId, useMemo, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import {
  getProjectDocsHealth,
  postProjectDocsHealth,
  type DocsHealthCluster,
  type DocsHealthClusterSuppression,
  type DocsHealthFinding,
  type DocsHealthProjectPayload,
} from '../api/docsHealth'
import { ProjectLocalNav } from '../components/projects'
import { PageHeader, StatePanel, TechnicalDetails } from '../components/page'
import { chargeMdCandidates } from '../lib/copilotPageEvidence'
import { formatDocsHealthProjectCopilotContext } from '../lib/docsHealthCopilotContext'
import { useSetLensesCopilotPageScope } from '../context/LensesCopilotPageScopeContext'
import { useStudioCommandBar } from '../context/StudioCommandBarContext'
import { ROUTE_SUBTITLE as SUB, STUDIO_VOCAB } from '../nav/studioVisibleCopy'

export function ProjectDocsHealthMasterPage() {
  const { name = '' } = useParams()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const decoded = decodeURIComponent(name)
  const enc = encodeURIComponent(decoded)
  const mainId = useId()
  const cmd = useStudioCommandBar()
  const setCopilotScope = useSetLensesCopilotPageScope()
  const relatedMdRelPaths = useMemo(
    () => chargeMdCandidates(decoded || undefined),
    [decoded],
  )

  const [data, setData] = useState<DocsHealthProjectPayload | null>(null)
  const [loading, setLoading] = useState(true)
  const [banner, setBanner] = useState<string | null>(null)
  const [clusterIndex, setClusterIndex] = useState(0)
  const [busy, setBusy] = useState<string | null>(null)
  const [suppressReason, setSuppressReason] = useState('')
  const [ktloSummary, setKtloSummary] = useState('')
  const [ktloEvidence, setKtloEvidence] = useState('')
  const [ktloNext, setKtloNext] = useState('')

  const load = useCallback(() => {
    if (!decoded) return
    setLoading(true)
    void getProjectDocsHealth(decoded)
      .then((d) => setData(d))
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [decoded])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    if (!decoded) return
    const head = `Forge Studio · Docs health (master) · ${decoded}`
    const detail = formatDocsHealthProjectCopilotContext(decoded, 'master', data)
    const pageContextSummary = detail ? `${head}\n\n${detail}` : head
    setCopilotScope({
      route: 'docs-health-master',
      projectSlug: decoded,
      scopeSite: decoded,
      pageContextSummary,
      relatedMdRelPaths,
    })
  }, [data, decoded, relatedMdRelPaths, setCopilotScope])

  const suppressedIds = useMemo(() => {
    const raw: DocsHealthClusterSuppression[] = data?.cluster_suppressions ?? []
    return new Set(raw.map((s) => s.cluster_id).filter(Boolean) as string[])
  }, [data?.cluster_suppressions])

  const latest = data?.latest_run as
    | {
        id?: string
        findings?: DocsHealthFinding[]
        clusters?: DocsHealthCluster[]
      }
    | undefined

  const clusters = useMemo(() => {
    const cs = latest?.clusters ?? []
    return cs.filter((c) => c.id && !suppressedIds.has(String(c.id)))
  }, [latest?.clusters, suppressedIds])

  useEffect(() => {
    const cid = searchParams.get('cluster')?.trim()
    if (!cid || !clusters.length) return
    const idx = clusters.findIndex((c) => String(c.id) === cid)
    if (idx >= 0) setClusterIndex(idx)
  }, [searchParams, clusters])

  const current = clusters[clusterIndex] ?? null
  const findings = latest?.findings ?? []
  const clusterFindings = useMemo(() => {
    if (!current?.finding_ids?.length) return []
    const ids = new Set(current.finding_ids)
    return findings.filter((f) => f.id && ids.has(f.id))
  }, [current, findings])

  const startSession = async () => {
    if (!decoded || !latest?.id || !current?.id) return
    setBusy('session')
    setBanner(null)
    try {
      const out = await postProjectDocsHealth(decoded, {
        op: 'create_session',
        cluster_id: current.id,
        run_id: latest.id,
      })
      const sid = (out.session as { id?: string } | undefined)?.id
      if (sid) {
        navigate(`/projects/${enc}/docs-health/session/${encodeURIComponent(sid)}`)
      } else {
        setBanner('Could not start session.')
      }
    } catch {
      setBanner('Session start failed.')
    } finally {
      setBusy(null)
    }
  }

  const submitSuppress = async () => {
    if (!decoded || !current?.id || suppressReason.trim().length < 3) {
      setBanner('Add a suppression reason (at least 3 characters).')
      return
    }
    setBusy('suppress')
    setBanner(null)
    try {
      const out = await postProjectDocsHealth(decoded, {
        op: 'suppress_cluster',
        cluster_id: current.id,
        reason: suppressReason.trim(),
        run_id: latest?.id,
      })
      if ((out as { ok?: boolean }).ok) {
        setBanner('Cluster suppressed for this workspace view.')
        setSuppressReason('')
        setClusterIndex(0)
        load()
      } else {
        setBanner('Could not record suppression.')
      }
    } catch {
      setBanner('Suppression failed.')
    } finally {
      setBusy(null)
    }
  }

  const submitKtlo = async () => {
    if (!decoded || !ktloSummary.trim() && !ktloEvidence.trim()) {
      setBanner('Add a summary or evidence for the KTLO ticket.')
      return
    }
    setBusy('ktlo')
    setBanner(null)
    try {
      const out = await postProjectDocsHealth(decoded, {
        op: 'ktlo_ticket',
        cluster_id: current?.id,
        run_id: latest?.id,
        title: `Docs: ${current?.label ?? 'cluster'}`,
        summary: ktloSummary.trim(),
        evidence: ktloEvidence.trim(),
        next_steps: ktloNext.trim(),
      })
      if ((out as { ok?: boolean }).ok) {
        setBanner('KTLO work item created — see Work → Documentation follow-ups.')
        setKtloSummary('')
        setKtloEvidence('')
        setKtloNext('')
        load()
      } else {
        setBanner('Could not create KTLO item.')
      }
    } catch {
      setBanner('KTLO creation failed.')
    } finally {
      setBusy(null)
    }
  }

  if (!decoded) {
    return <StatePanel variant="not_configured" title="Missing project" description="Pick a project from the list." />
  }

  return (
    <>
      <PageHeader
        title={STUDIO_VOCAB.docsHealthMaster}
        purpose={SUB.docsHealthMaster}
        secondaryMenuItems={[
          { key: 'docs', to: `/projects/${enc}/docs-health`, label: STUDIO_VOCAB.docsHealth },
          { key: 'dash', to: `/projects/${enc}`, label: STUDIO_VOCAB.projectDashboard },
        ]}
      />
      <ProjectLocalNav projectName={decoded} />

      {banner ? (
        <p className="forge-support" role="status" aria-live="polite">
          {banner}
        </p>
      ) : null}

      {loading ? (
        <StatePanel variant="loading" title="Loading Master mode" description="Reading the latest scan for this repository." />
      ) : !data?.ok ? (
        <StatePanel variant="error" title="Docs Health unavailable" description="The server did not return docs health data for this project." />
      ) : !latest?.id || !clusters.length ? (
        <StatePanel
          variant="not_configured"
          title="No clusters to review"
          description="Run a scan, or clear suppressions, to use Master mode on grouped findings."
          actions={
            <Link className="le-btn le-btn--primary" to={`/projects/${enc}/docs-health`}>
              Back to Docs health
            </Link>
          }
        />
      ) : (
        <section id={mainId} className="le-panel" aria-labelledby={`${mainId}-h`}>
          <h2 id={`${mainId}-h`} className="le-panel__title">
            Cluster {clusterIndex + 1} of {clusters.length}
          </h2>
          <p className="forge-support">
            Master mode shows one cluster at a time: what is wrong, why it matters, score impact, and safe next actions.
            Model calls stay <strong>local-first</strong> (see AI Setup); external providers are used only when configured
            and policy allows.
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.75rem' }}>
            <button
              type="button"
              className="le-btn le-btn--small"
              disabled={clusterIndex <= 0}
              onClick={() => setClusterIndex((i) => Math.max(0, i - 1))}
            >
              Previous cluster
            </button>
            <button
              type="button"
              className="le-btn le-btn--small"
              disabled={clusterIndex >= clusters.length - 1}
              onClick={() => setClusterIndex((i) => Math.min(clusters.length - 1, i + 1))}
            >
              Skip — next cluster
            </button>
          </div>

          <article className="le-panel" style={{ padding: '0.85rem', marginBottom: '1rem' }} aria-label="Current cluster">
            <h3 style={{ marginTop: 0 }}>{current?.label ?? 'Cluster'}</h3>
            <p className="le-muted" style={{ fontSize: '0.9rem' }}>
              {current?.finding_ids?.length ?? 0} finding(s)
              {typeof current?.expected_score_gain_if_cleared === 'number' ? (
                <>
                  {' '}
                  · up to <strong>+{current.expected_score_gain_if_cleared}</strong> pts if cleared
                </>
              ) : null}
            </p>
            {current?.suggested_next ? (
              <p className="forge-support">
                <strong>Recommended next:</strong> {current.suggested_next}
              </p>
            ) : null}
            <h4 className="le-muted" style={{ fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              What is wrong
            </h4>
            <ul style={{ paddingLeft: '1.2rem' }}>
              {clusterFindings.map((f) => (
                <li key={f.id} style={{ marginBottom: '0.5rem' }}>
                  <strong>{f.title}</strong>
                  <div className="le-muted" style={{ fontSize: '0.85rem' }}>
                    {f.severity} · {f.category}
                    {f.fixability ? ` · ${f.fixability}` : null}
                  </div>
                  {f.summary ? <p className="forge-support">{f.summary}</p> : null}
                </li>
              ))}
            </ul>
            <h4 className="le-muted" style={{ fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Why it matters
            </h4>
            <ul style={{ paddingLeft: '1.2rem' }}>
              {clusterFindings.map((f) =>
                f.why_it_matters ? (
                  <li key={`${f.id}-why`} className="forge-support">
                    {f.why_it_matters}
                  </li>
                ) : null,
              )}
            </ul>
          </article>

          <div
            role="group"
            aria-label="Master actions"
            style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '1rem' }}
          >
            <button type="button" className="le-btn le-btn--primary" disabled={busy === 'session'} onClick={() => void startSession()}>
              {busy === 'session' ? 'Opening…' : 'Draft fix — open session'}
            </button>
            <button
              type="button"
              className="le-btn"
              onClick={() =>
                cmd.open('ask', {
                  initialQuery: `Project “${decoded}”, Master mode cluster: ${current?.label ?? ''}. What is the safest documentation change?`,
                })
              }
            >
              Ask a question
            </button>
            <Link className="le-btn" to={`/projects/${enc}/docs-health`}>
              Full checklist view
            </Link>
          </div>

          <section className="le-panel" aria-labelledby={`${mainId}-ktlo`} style={{ marginBottom: '1rem' }}>
            <h3 id={`${mainId}-ktlo`} className="le-panel__title">
              Create KTLO ticket
            </h3>
            <p className="forge-support">
              For ticket-only or manual fixes, or when auto-patch is unsafe, create tracked work with links back to Docs
              health, Master mode, and Knowledge (workspace markdown).
            </p>
            <label className="forge-support" htmlFor={`${mainId}-ks`}>
              Summary
            </label>
            <textarea
              id={`${mainId}-ks`}
              className="le-input"
              rows={2}
              value={ktloSummary}
              onChange={(e) => setKtloSummary(e.target.value)}
              style={{ width: '100%', marginTop: '0.25rem' }}
            />
            <label className="forge-support" htmlFor={`${mainId}-ke`} style={{ display: 'block', marginTop: '0.5rem' }}>
              Evidence
            </label>
            <textarea
              id={`${mainId}-ke`}
              className="le-input"
              rows={3}
              value={ktloEvidence}
              onChange={(e) => setKtloEvidence(e.target.value)}
              style={{ width: '100%', marginTop: '0.25rem' }}
            />
            <label className="forge-support" htmlFor={`${mainId}-kn`} style={{ display: 'block', marginTop: '0.5rem' }}>
              Suggested next steps
            </label>
            <textarea
              id={`${mainId}-kn`}
              className="le-input"
              rows={2}
              value={ktloNext}
              onChange={(e) => setKtloNext(e.target.value)}
              style={{ width: '100%', marginTop: '0.25rem' }}
            />
            <button
              type="button"
              className="le-btn le-btn--primary"
              style={{ marginTop: '0.5rem' }}
              disabled={busy === 'ktlo'}
              onClick={() => void submitKtlo()}
            >
              {busy === 'ktlo' ? 'Creating…' : 'Create KTLO item'}
            </button>
          </section>

          <section className="le-panel" aria-labelledby={`${mainId}-sup`}>
            <h3 id={`${mainId}-sup`} className="le-panel__title">
              Suppress cluster (with reason)
            </h3>
            <p className="forge-support">Recorded locally under Docs Health store; use for false positives or accepted risk.</p>
            <textarea
              className="le-input"
              rows={2}
              value={suppressReason}
              onChange={(e) => setSuppressReason(e.target.value)}
              placeholder="Reason (required, min 3 characters)"
              style={{ width: '100%' }}
              aria-label="Suppression reason"
            />
            <button
              type="button"
              className="le-btn"
              style={{ marginTop: '0.5rem' }}
              disabled={busy === 'suppress'}
              onClick={() => void submitSuppress()}
            >
              {busy === 'suppress' ? 'Saving…' : 'Suppress cluster'}
            </button>
          </section>

          <TechnicalDetails summary="Patch safety and branching" defaultOpen={false}>
            <ul className="forge-support">
              <li>Session flow uses rule precheck then reviewer JSON — preview diffs before Apply.</li>
              <li>
                Apply writes the working tree only; create the session&apos;s suggested branch locally (typically{' '}
                <code>feature/docs-health-…</code>, or <code>docs-health/…</code> if the project sets{' '}
                <code>forge/branching.yml</code> to legacy style) before applying.
              </li>
              <li>No automatic merge to main.</li>
            </ul>
          </TechnicalDetails>
        </section>
      )}
    </>
  )
}
