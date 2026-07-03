import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { apiGetJson, apiPostJson } from '../api/http'
import { PageHeader, StatePanel } from '../components/page'
import { FoundryCapabilitiesCard } from '../components/foundry/FoundryCapabilitiesCard'
import { FoundryPlanCard } from '../components/foundry/FoundryPlanCard'
import { useWorkspace } from '../context/WorkspaceContext'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'
import type {
  FoundryCapabilities,
  FoundryIntake,
  FoundryPlan,
  FoundryRun,
  FoundryRunsList,
} from '../lib/foundryTypes'
import { KNOWLEDGE_PUBLISH_COPILOT, ROUTE_SUBTITLE, STUDIO_VOCAB } from '../nav/studioVisibleCopy'

const LEVELS = ['L1', 'L2', 'L3'] as const

export function FoundryPage() {
  useLensesCopilotPage({ route: 'knowledge', defaultQuery: KNOWLEDGE_PUBLISH_COPILOT.foundry })
  const navigate = useNavigate()
  const { state: workspace } = useWorkspace()
  const projects = useMemo(
    () => (workspace?.children ?? []).filter((c) => c.is_git !== false).map((c) => c.name),
    [workspace],
  )

  const [enabled, setEnabled] = useState<boolean | null>(null)
  const [capabilities, setCapabilities] = useState<FoundryCapabilities | null>(null)
  const [runs, setRuns] = useState<FoundryRun[]>([])
  const [project, setProject] = useState('forge-df-test-project')
  const [target, setTarget] = useState('src/dfcalc/engine.py')
  const [goal, setGoal] = useState('fix failing multiply')
  const [level, setLevel] = useState<(typeof LEVELS)[number]>('L1')
  const [chat, setChat] = useState('')
  const [plan, setPlan] = useState<FoundryPlan | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadMeta = useCallback(async () => {
    try {
      const [en, cap, list] = await Promise.all([
        apiGetJson<{ enabled?: boolean }>('/api/foundry/enabled'),
        apiGetJson<FoundryCapabilities>('/api/foundry/capabilities'),
        apiGetJson<FoundryRunsList>('/api/foundry/runs'),
      ])
      setEnabled(Boolean(en.enabled))
      setCapabilities(cap)
      setRuns(list.runs ?? [])
      setError(null)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load Foundry')
      setEnabled(false)
    }
  }, [])

  useEffect(() => {
    void loadMeta()
  }, [loadMeta])

  const onIntake = async () => {
    if (!chat.trim()) return
    setBusy(true)
    try {
      const intake = await apiPostJson<FoundryIntake>('/api/foundry/intake', {
        message: chat,
        project,
      })
      if (intake.goal) setGoal(intake.goal)
      if (intake.target) setTarget(intake.target)
      if (intake.project) setProject(intake.project)
      if (intake.level === 'L1' || intake.level === 'L2' || intake.level === 'L3') setLevel(intake.level)
    } finally {
      setBusy(false)
    }
  }

  const onProposePlan = async () => {
    setBusy(true)
    try {
      const body = {
        goal,
        project,
        target,
        level,
        execution_mode: 'draft',
      }
      const p = await apiPostJson<FoundryPlan>('/api/foundry/plan', body)
      setPlan(p)
    } finally {
      setBusy(false)
    }
  }

  const onRunDraft = async () => {
    setBusy(true)
    try {
      const body = {
        goal,
        project,
        target,
        level,
        execution_mode: 'draft',
        worker: 'fake',
        plan: plan ?? undefined,
      }
      const created = await apiPostJson<FoundryRun>('/api/foundry/runs', body)
      if (created.id) navigate(`/foundry/runs/${encodeURIComponent(created.id)}`)
      await loadMeta()
    } finally {
      setBusy(false)
    }
  }

  if (enabled === false) {
    return (
      <>
        <PageHeader title={STUDIO_VOCAB.foundry} subtitle={<>{ROUTE_SUBTITLE.foundry}</>} />
        <StatePanel
          variant="empty"
          title="Foundry is off"
          description="Enable the orchestration graph and agentic bridge (B3). Set LENSES_EXPERIMENTAL_FOUNDRY=1 when needed."
        />
      </>
    )
  }

  return (
    <>
      <PageHeader title={STUDIO_VOCAB.foundry} subtitle={<>{ROUTE_SUBTITLE.foundry}</>} />
      {error ? <StatePanel variant="error" title="Load error" technicalDetail={error} /> : null}
      <section className="le-stack" style={{ marginTop: '1rem' }}>
        <FoundryCapabilitiesCard capabilities={capabilities} />

        <section className="le-card" aria-label="Foundry composer">
          <h2 className="le-card__title">Compose a bounded L1 run</h2>
          <p className="le-muted">
            Pick a workspace project, state a goal, and propose a plan. Humans seed failing tests; Dark Factory
            drafts fixes. You always confirm before promote.
          </p>

          <div className="le-form-grid" style={{ marginTop: '0.75rem' }}>
            <label>
              @project
              <select value={project} onChange={(e) => setProject(e.target.value)}>
                {projects.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </label>
            <label>
              #target
              <input value={target} onChange={(e) => setTarget(e.target.value)} placeholder="src/…" />
            </label>
            <label>
              goal
              <input value={goal} onChange={(e) => setGoal(e.target.value)} />
            </label>
          </div>

          <div className="le-btn-row" style={{ marginTop: '0.5rem' }} role="group" aria-label="Autonomy level">
            {LEVELS.map((lv) => {
              const stub = lv !== 'L1'
              const active = level === lv
              return (
                <button
                  key={lv}
                  type="button"
                  className={`le-btn le-btn--small${active ? ' le-btn--primary' : ''}`}
                  disabled={stub}
                  title={stub ? 'Requires Dark Factory L2/L3 (not wired)' : undefined}
                  onClick={() => setLevel(lv)}
                >
                  {lv}
                </button>
              )
            })}
            <span className="le-muted">mode: draft</span>
          </div>

          <div className="le-btn-row" style={{ marginTop: '0.75rem' }}>
            <button type="button" className="le-btn" disabled={busy} onClick={() => void onProposePlan()}>
              Propose plan
            </button>
          </div>
        </section>

        <section className="le-card" aria-label="Agentic goal intake">
          <h2 className="le-card__title">Chat intake (fallback parser)</h2>
          <textarea
            className="le-textarea"
            rows={3}
            value={chat}
            onChange={(e) => setChat(e.target.value)}
            placeholder="e.g. fix failing multiply for @forge-df-test-project #src/dfcalc/engine.py L1"
          />
          <div className="le-btn-row" style={{ marginTop: '0.5rem' }}>
            <button type="button" className="le-btn le-btn--small" disabled={busy} onClick={() => void onIntake()}>
              Parse into composer
            </button>
          </div>
        </section>

        <FoundryPlanCard plan={plan} busy={busy} onRunDraft={() => void onRunDraft()} />

        <section className="le-card" aria-label="Recent runs">
          <h2 className="le-card__title">Recent runs</h2>
          {runs.length ? (
            <ul className="le-list">
              {runs.map((r) => (
                <li key={r.id}>
                  <Link to={`/foundry/runs/${encodeURIComponent(r.id ?? '')}`}>
                    {r.goal ?? r.id} — {r.status}
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <p className="le-muted">No runs yet.</p>
          )}
        </section>
      </section>
    </>
  )
}
