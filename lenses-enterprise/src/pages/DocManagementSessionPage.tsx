import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import {
  cancelDocManagementSession,
  getDocManagementCatalog,
  getDocManagementSession,
  promoteDocManagementSession,
  rollbackDocManagementSession,
  runDocManagementSession,
  saveDocManagementDecisions,
  saveDocManagementWizard,
  submitDocManagementIntake,
  type DocManagementSession,
} from '../api/docManagement'
import { PageHeader, StatePanel } from '../components/page'
import { useDocManagementSessionStream } from '../hooks/useDocManagementSessionStream'
import {
  DOC_MGMT_WORKFLOW_LABELS,
  DOC_MGMT_WORKFLOW_ORDER,
  WIZARD_STEPS,
} from '../lib/docManagementStageFlow'
import { docManagementFeatureEnabled } from '../util/experimentalFlags'

function stageIndex(stage: string | undefined): number {
  const i = DOC_MGMT_WORKFLOW_ORDER.indexOf(stage as (typeof DOC_MGMT_WORKFLOW_ORDER)[number])
  return i >= 0 ? i : 0
}

export function DocManagementSessionPage() {
  const { sessionId = '' } = useParams()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const blogSlug = searchParams.get('blog_slug') || ''

  const [session, setSession] = useState<DocManagementSession | null>(null)
  const [wizardStep, setWizardStep] = useState(0)
  const [pasteText, setPasteText] = useState('')
  const [url, setUrl] = useState('')
  const [intakeSource, setIntakeSource] = useState<'paste' | 'zip' | 'url' | 'blog'>('paste')
  const [personas, setPersonas] = useState<Array<{ persona_id: string; label: string }>>([])
  const [surfaces, setSurfaces] = useState<Array<{ surface_id: string; label: string }>>([])
  const [selectedSurfaces, setSelectedSurfaces] = useState<string[]>(['forgesdlc_blog'])
  const [persona, setPersona] = useState('architect')
  const [useLlm, setUseLlm] = useState(false)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [reviewer, setReviewer] = useState('studio_operator')

  const live = useDocManagementSessionStream(
    sessionId,
    Boolean(sessionId) && ['running', 'awaiting_approval'].includes(session?.status || ''),
  )

  const load = useCallback(async () => {
    if (!sessionId) return
    const res = await getDocManagementSession(sessionId)
    setSession(res.session)
    const w = res.session.wizard
    if (w?.persona) setPersona(w.persona)
    if (w?.target_surfaces?.length) setSelectedSurfaces(w.target_surfaces)
    if (w?.use_llm) setUseLlm(Boolean(w.use_llm))
    if (w?.intake_source === 'blog' && w.blog_slug) setIntakeSource('blog')
  }, [sessionId])

  useEffect(() => {
    if (!docManagementFeatureEnabled() || !sessionId) return
    void load()
    void getDocManagementCatalog().then((c) => {
      setPersonas(c.personas || [])
      setSurfaces(c.surfaces || [])
    })
  }, [sessionId, load])

  useEffect(() => {
    if (live.session) setSession(live.session)
  }, [live.session])

  useEffect(() => {
    if (blogSlug && sessionId && session?.status === 'draft') {
      setIntakeSource('blog')
      setWizardStep(0)
    }
  }, [blogSlug, sessionId, session?.status])

  const seeds = session?.intake?.seeds || []
  const workflowStage = session?.workflow?.stage || 'intake'
  const stageLabels = useMemo(
    () =>
      DOC_MGMT_WORKFLOW_ORDER.map((id) => ({
        id,
        label: DOC_MGMT_WORKFLOW_LABELS[id],
        status:
          stageIndex(workflowStage) > stageIndex(id)
            ? ('completed' as const)
            : workflowStage === id
              ? ('in_progress' as const)
              : ('not_started' as const),
      })),
    [workflowStage],
  )

  const onIntake = async () => {
    if (!sessionId) return
    setBusy(true)
    setMessage(null)
    try {
      let zipBase64: string | undefined
      if (intakeSource === 'zip') {
        const input = document.getElementById('dm-zip-input') as HTMLInputElement | null
        const file = input?.files?.[0]
        if (!file) throw new Error('Select a zip file')
        const buf = await file.arrayBuffer()
        zipBase64 = btoa(String.fromCharCode(...new Uint8Array(buf)))
      }
      await submitDocManagementIntake(sessionId, {
        intake_source: intakeSource,
        text: intakeSource === 'paste' ? pasteText : undefined,
        zip_base64: zipBase64,
        url: intakeSource === 'url' ? url : undefined,
        blog_slug: intakeSource === 'blog' ? blogSlug || session?.wizard?.blog_slug || '' : undefined,
      })
      await load()
      setWizardStep(1)
      setMessage('Intake normalized')
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'intake_failed')
    } finally {
      setBusy(false)
    }
  }

  const onSaveWizard = async () => {
    if (!sessionId) return
    setBusy(true)
    try {
      await saveDocManagementWizard(sessionId, {
        step_index: wizardStep,
        persona,
        target_surfaces: selectedSurfaces,
        use_llm: useLlm,
      })
      await load()
      setMessage('Wizard settings saved')
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'wizard_save_failed')
    } finally {
      setBusy(false)
    }
  }

  const onRun = async () => {
    if (!sessionId) return
    setBusy(true)
    try {
      await onSaveWizard()
      await runDocManagementSession(sessionId)
      await load()
      setMessage('Hydration pipeline finished or awaiting approval')
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'run_failed')
    } finally {
      setBusy(false)
    }
  }

  const onApproveAll = async () => {
    if (!sessionId || !seeds.length) return
    setBusy(true)
    try {
      const decisions = seeds.map((s) => ({
        target: s.name.replace(/\.md$/, ''),
        decision: 'promote_as_is',
        surfaces: selectedSurfaces,
        notes: 'Studio bulk approve',
      }))
      await saveDocManagementDecisions(sessionId, reviewer, decisions)
      await load()
      setMessage('Reviewer manifest saved')
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'approve_failed')
    } finally {
      setBusy(false)
    }
  }

  const onPromote = async (dryRun: boolean) => {
    if (!sessionId) return
    setBusy(true)
    try {
      const res = await promoteDocManagementSession(sessionId, dryRun)
      setMessage(dryRun ? 'Dry-run promote complete' : `Promote: ${JSON.stringify(res.result)}`)
      await load()
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'promote_failed')
    } finally {
      setBusy(false)
    }
  }

  const onRollback = async () => {
    if (!sessionId) return
    setBusy(true)
    try {
      await rollbackDocManagementSession(sessionId)
      await load()
      setMessage('Rollback requested')
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'rollback_failed')
    } finally {
      setBusy(false)
    }
  }

  const onCancel = async () => {
    if (!sessionId) return
    await cancelDocManagementSession(sessionId)
    navigate('/doc-management')
  }

  if (!docManagementFeatureEnabled()) {
    return <StatePanel variant="not_configured" title="Disabled" description="Enable VITE_EXPERIMENTAL_DOC_MANAGEMENT." />
  }

  if (!session) return <p>Loading session…</p>

  return (
    <div className="studio-page doc-management-session">
      <PageHeader
        title={session.display_name}
        subtitle={`Session ${session.id} · ${session.status} · ${session.forge_run_id || ''}`}
        actions={
          <Link to="/doc-management" className="ks-btn">
            Hub
          </Link>
        }
      />
      {message ? <p className="dm-banner">{message}</p> : null}

      <ol className="dm-workflow-stages">
        {stageLabels.map((s) => (
          <li key={s.id} data-status={s.status}>
            {s.label}
          </li>
        ))}
      </ol>

      {session.status === 'draft' || seeds.length === 0 ? (
        <section className="dm-wizard">
          <h2>Wizard — {WIZARD_STEPS[wizardStep]?.label}</h2>
          {wizardStep === 0 ? (
            <div>
              <label>
                <input
                  type="radio"
                  checked={intakeSource === 'paste'}
                  onChange={() => setIntakeSource('paste')}
                />{' '}
                Paste Markdown
              </label>
              <label>
                <input type="radio" checked={intakeSource === 'zip'} onChange={() => setIntakeSource('zip')} /> Zip of
                .md files
              </label>
              <label>
                <input type="radio" checked={intakeSource === 'url'} onChange={() => setIntakeSource('url')} /> URL
              </label>
              <label>
                <input type="radio" checked={intakeSource === 'blog'} onChange={() => setIntakeSource('blog')} /> Blog
                post
              </label>
              {intakeSource === 'paste' ? (
                <textarea rows={12} value={pasteText} onChange={(e) => setPasteText(e.target.value)} />
              ) : null}
              {intakeSource === 'url' ? <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://…" /> : null}
              {intakeSource === 'zip' ? <input id="dm-zip-input" type="file" accept=".zip" /> : null}
              {intakeSource === 'blog' ? (
                <p>
                  Blog slug: <code>{blogSlug || session.wizard?.blog_slug || '(pick from Blog)'}</code>
                </p>
              ) : null}
              <button type="button" className="ks-btn ks-btn-primary" disabled={busy} onClick={() => void onIntake()}>
                Normalize intake
              </button>
            </div>
          ) : null}
          {wizardStep >= 1 ? (
            <div>
              <h3>Seeds ({seeds.length})</h3>
              <ul>
                {seeds.map((s) => (
                  <li key={s.path}>
                    {s.name} — {s.status}
                  </li>
                ))}
              </ul>
              <label>
                Persona
                <select value={persona} onChange={(e) => setPersona(e.target.value)}>
                  {personas.map((p) => (
                    <option key={p.persona_id} value={p.persona_id}>
                      {p.label}
                    </option>
                  ))}
                </select>
              </label>
              <fieldset>
                <legend>Target surfaces</legend>
                {surfaces.map((s) => (
                  <label key={s.surface_id}>
                    <input
                      type="checkbox"
                      checked={selectedSurfaces.includes(s.surface_id)}
                      onChange={(e) => {
                        setSelectedSurfaces((cur) =>
                          e.target.checked ? [...cur, s.surface_id] : cur.filter((x) => x !== s.surface_id),
                        )
                      }}
                    />{' '}
                    {s.label}
                  </label>
                ))}
              </fieldset>
              <label>
                <input type="checkbox" checked={useLlm} onChange={(e) => setUseLlm(e.target.checked)} /> Use governed
                LLM (claim extraction)
              </label>
              <div className="dm-wizard-nav">
                <button type="button" className="ks-btn" disabled={busy} onClick={() => void onSaveWizard()}>
                  Save wizard
                </button>
                <button type="button" className="ks-btn ks-btn-primary" disabled={busy} onClick={() => void onRun()}>
                  Run hydration
                </button>
              </div>
            </div>
          ) : null}
        </section>
      ) : null}

      {(session.pack_artifacts?.length || 0) > 0 ? (
        <section>
          <h2>Review pack</h2>
          {session.pack_artifacts?.map((p) => (
            <article key={p.slug} className="dm-pack-artifact">
              <h3>{p.slug}</h3>
              <p>Artifacts: {p.artifacts.join(', ')}</p>
              {p.hydration_brief_markdown ? (
                <pre className="dm-brief-preview">{p.hydration_brief_markdown.slice(0, 2000)}</pre>
              ) : null}
            </article>
          ))}
        </section>
      ) : null}

      {session.status === 'awaiting_approval' || session.reviewer_decision_manifest ? (
        <section className="dm-approve">
          <h2>Approve & promote</h2>
          <label>
            Reviewer
            <input value={reviewer} onChange={(e) => setReviewer(e.target.value)} />
          </label>
          <button type="button" className="ks-btn" disabled={busy} onClick={() => void onApproveAll()}>
            Save manifest (promote all seeds)
          </button>
          <button type="button" className="ks-btn" disabled={busy} onClick={() => void onPromote(true)}>
            Dry-run promote
          </button>
          <button type="button" className="ks-btn ks-btn-primary" disabled={busy} onClick={() => void onPromote(false)}>
            Apply promote & commit
          </button>
          <button type="button" className="ks-btn" disabled={busy} onClick={() => void onRollback()}>
            Rollback
          </button>
        </section>
      ) : null}

      <button type="button" className="ks-btn dm-cancel" disabled={busy} onClick={() => void onCancel()}>
        Cancel session
      </button>
    </div>
  )
}
