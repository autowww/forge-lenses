import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useWorkspace } from '../../context/WorkspaceContext'
import { wbsBacklogPickerLabel } from '../../util/planScopeCluster'
import { STUDIO_VOCAB } from '../../nav/studioVisibleCopy'
import { recordFirstRunWizardStep } from '../../telemetry/studioTelemetry'

const DISMISS_KEY = 'lenses.studio.firstRunWizard.dismissed'

type Step = 1 | 2 | 3

function readDismissed(): boolean {
  try {
    return localStorage.getItem(DISMISS_KEY) === '1'
  } catch {
    return false
  }
}

function writeDismissed() {
  try {
    localStorage.setItem(DISMISS_KEY, '1')
  } catch {
    /* ignore */
  }
}

/**
 * First-run wizard: pick project → backlog → confirm scope before diving into Plan / Today.
 */
export function StudioFirstRunWizard() {
  const { state } = useWorkspace()
  const navigate = useNavigate()
  const [dismissed, setDismissed] = useState(readDismissed)
  const [step, setStep] = useState<Step>(1)
  const [project, setProject] = useState('')
  const [backlogPath, setBacklogPath] = useState('')

  const gitRepos = useMemo(() => {
    const children = Array.isArray(state?.children) ? state.children : []
    return children.filter((c) => c.is_git).map((c) => String(c.name ?? '').trim()).filter(Boolean)
  }, [state?.children])

  const backlogOptions = useMemo(() => {
    const wbs = Array.isArray(state?.wbs) ? state.wbs : []
    const filtered = project
      ? wbs.filter((w) => String(w.repo_hint ?? '').trim() === project || w.rel_path.startsWith(`${project}/`))
      : wbs
    return filtered.map((w) => ({
      rel_path: w.rel_path,
      repo_hint: String(w.repo_hint ?? '').trim(),
      label: wbsBacklogPickerLabel(w.rel_path, String(w.repo_hint ?? '')),
    }))
  }, [state?.wbs, project])

  useEffect(() => {
    if (!project && gitRepos.length === 1) setProject(gitRepos[0]!)
  }, [gitRepos, project])

  useEffect(() => {
    if (!backlogPath && backlogOptions.length === 1) setBacklogPath(backlogOptions[0]!.rel_path)
  }, [backlogOptions, backlogPath])

  const finish = useCallback(() => {
    recordFirstRunWizardStep(step, 'finish')
    writeDismissed()
    setDismissed(true)
    const row = backlogOptions.find((b) => b.rel_path === backlogPath)
    const q = new URLSearchParams()
    if (project) q.set('repo', project)
    if (backlogPath) q.set('wbs_p', backlogPath)
    if (row?.repo_hint) q.set('repo', row.repo_hint)
    q.set('tab', 'today')
    navigate(`/plan?${q.toString()}`)
  }, [backlogOptions, backlogPath, navigate, project, step])

  const skip = useCallback(() => {
    recordFirstRunWizardStep(step, 'skip')
    writeDismissed()
    setDismissed(true)
  }, [step])

  useEffect(() => {
    if (!dismissed) recordFirstRunWizardStep(step, 'view')
  }, [dismissed, step])

  if (dismissed || !state || gitRepos.length === 0) return null

  return (
    <section className="le-card le-first-run-wizard" aria-label="First-run setup" style={{ marginBottom: '1rem' }}>
      <h2 className="le-panel__title" style={{ marginTop: 0 }}>
        Get to {STUDIO_VOCAB.today} in three steps
      </h2>
      <p className="forge-support">
        Pick a project and backlog once — Studio keeps human labels in scope bars instead of raw file paths.
      </p>
      <ol className="le-first-run-wizard__steps" style={{ paddingLeft: '1.25rem', margin: '0.75rem 0' }}>
        <li aria-current={step === 1 ? 'step' : undefined}>
          <strong>Project</strong>
          {step > 1 && project ? ` — ${project}` : null}
        </li>
        <li aria-current={step === 2 ? 'step' : undefined}>
          <strong>Backlog</strong>
          {step > 2 && backlogPath
            ? ` — ${wbsBacklogPickerLabel(backlogPath, project)}`
            : null}
        </li>
        <li aria-current={step === 3 ? 'step' : undefined}>
          <strong>Confirm</strong>
        </li>
      </ol>

      {step === 1 ? (
        <div className="le-form-row" style={{ flexDirection: 'column', alignItems: 'stretch', maxWidth: '24rem' }}>
          <label>
            Git repository
            <select className="le-select" value={project} onChange={(e) => setProject(e.target.value)} style={{ display: 'block', marginTop: '0.25rem', width: '100%' }}>
              <option value="">— choose —</option>
              {gitRepos.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </label>
          <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
            <button type="button" className="le-btn le-btn--primary" disabled={!project} onClick={() => setStep(2)}>
              Next
            </button>
            <button type="button" className="le-btn" onClick={skip}>
              Skip wizard
            </button>
          </div>
        </div>
      ) : null}

      {step === 2 ? (
        <div className="le-form-row" style={{ flexDirection: 'column', alignItems: 'stretch', maxWidth: '28rem' }}>
          <label>
            Work backlog
            <select
              className="le-select"
              value={backlogPath}
              onChange={(e) => setBacklogPath(e.target.value)}
              style={{ display: 'block', marginTop: '0.25rem', width: '100%' }}
            >
              <option value="">— choose —</option>
              {backlogOptions.map((b) => (
                <option key={b.rel_path} value={b.rel_path} title={b.rel_path}>
                  {b.label}
                </option>
              ))}
            </select>
          </label>
          <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
            <button type="button" className="le-btn" onClick={() => setStep(1)}>
              Back
            </button>
            <button type="button" className="le-btn le-btn--primary" disabled={!backlogPath} onClick={() => setStep(3)}>
              Next
            </button>
          </div>
        </div>
      ) : null}

      {step === 3 ? (
        <div>
          <p className="forge-support">
            Open <strong>{STUDIO_VOCAB.today}</strong> scoped to{' '}
            <strong>{project || 'workspace'}</strong>
            {backlogPath ? (
              <>
                {' '}
                · backlog <strong>{wbsBacklogPickerLabel(backlogPath, project)}</strong>
              </>
            ) : null}
            . You can change scope any time from the plan bar.
          </p>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <button type="button" className="le-btn le-btn--primary" onClick={finish}>
              Open {STUDIO_VOCAB.today}
            </button>
            <button type="button" className="le-btn" onClick={() => setStep(2)}>
              Back
            </button>
            <Link className="le-btn" to="/plan" onClick={skip}>
              Open plan without scope
            </Link>
          </div>
        </div>
      ) : null}
    </section>
  )
}
