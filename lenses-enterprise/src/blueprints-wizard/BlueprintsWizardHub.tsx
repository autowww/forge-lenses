import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'
import {
  createWizardSession,
  getBlueprintsWizardEnabled,
  listWizardSessions,
  type WizardSessionSummary,
} from '../api/blueprintsWizard'
import { StatePanel, TechnicalDetails } from '../components/page'
import { resolveUxFailure, type UxResolvedFailure } from '../lib/uxPageState'
import {
  BLUEPRINTS_WIZARD_HUB_COPY,
  KNOWLEDGE_PUBLISH_COPILOT,
  STUDIO_IA,
  STUDIO_VOCAB,
} from '../nav/studioVisibleCopy'

export function BlueprintsWizardHub() {
  useLensesCopilotPage({ route: 'knowledge', defaultQuery: KNOWLEDGE_PUBLISH_COPILOT.wizardHub })
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const legacySession = searchParams.get('session')

  const [sessions, setSessions] = useState<WizardSessionSummary[] | null>(null)
  const [wizardDisabled, setWizardDisabled] = useState(false)
  const [fetchFailure, setFetchFailure] = useState<UxResolvedFailure | null>(null)
  const [createFailure, setCreateFailure] = useState<UxResolvedFailure | null>(null)
  const [creating, setCreating] = useState(false)
  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => {
    if (legacySession && legacySession.trim()) {
      navigate(`session/${encodeURIComponent(legacySession.trim())}`, {
        replace: true,
      })
      setSearchParams({}, { replace: true })
    }
  }, [legacySession, navigate, setSearchParams])

  const load = useCallback((isManualRefresh = false) => {
    setFetchFailure(null)
    setWizardDisabled(false)
    if (isManualRefresh) setRefreshing(true)
    void (async () => {
      try {
        const ok = await getBlueprintsWizardEnabled()
        if (!ok) {
          setWizardDisabled(true)
          setSessions([])
          return
        }
        const rows = await listWizardSessions()
        setSessions(rows)
      } catch (e: unknown) {
        setSessions([])
        setFetchFailure(resolveUxFailure(e))
      } finally {
        if (isManualRefresh) setRefreshing(false)
      }
    })()
  }, [])

  useEffect(() => {
    load(false)
  }, [load])

  const onNew = useCallback(() => {
    setCreating(true)
    setCreateFailure(null)
    void (async () => {
      try {
        const { session_id } = await createWizardSession()
        navigate(`session/${encodeURIComponent(session_id)}`)
      } catch (e: unknown) {
        setCreateFailure(resolveUxFailure(e))
      } finally {
        setCreating(false)
      }
    })()
  }, [navigate])

  const onOpen = useCallback(
    (id: string) => {
      navigate(`session/${encodeURIComponent(id)}`)
    },
    [navigate],
  )

  if (sessions === null && !wizardDisabled && !fetchFailure) {
    return (
      <div className="ks-wizard-flow" style={{ maxWidth: '48rem' }}>
        <header style={{ marginBottom: '1rem' }}>
          <h1 className="le-h1">Blueprints Wizard</h1>
        </header>
        <StatePanel variant="loading" title="Loading wizard sessions" description="Checking whether Blueprints Wizard is available and listing saved drafts." />
      </div>
    )
  }

  const blocked = wizardDisabled || Boolean(fetchFailure)

  return (
    <div className="ks-wizard-flow" style={{ maxWidth: '48rem' }}>
      <header style={{ marginBottom: '1rem' }}>
        <h1 className="le-h1">Blueprints Wizard</h1>
        <p className="ks-wizard-flow__muted forge-support" style={{ marginBottom: '0.5rem' }}>
          <span className="le-shortcut-pill" title="AI-assisted; behavior and storage may change">
            Experimental
          </span>{' '}
          {STUDIO_IA.wizardExperimentalLead}
        </p>
        <p className="ks-wizard-flow__muted forge-support" style={{ marginBottom: '0.5rem' }}>
          {BLUEPRINTS_WIZARD_HUB_COPY.valueLead}
        </p>
        <p className="ks-wizard-flow__muted forge-support" style={{ marginBottom: '0.5rem' }}>
          {BLUEPRINTS_WIZARD_HUB_COPY.whenToUse}
        </p>
        <p className="ks-wizard-flow__muted forge-support">
          Choose a session below or start a new one. Drafts stay on the machine running Lenses (not in your git tree).
          For day-to-day delivery, use{' '}
          <Link to="/plan">{STUDIO_VOCAB.planSummary}</Link>, <Link to="/plan?tab=today">{STUDIO_VOCAB.today}</Link>, or{' '}
          <Link to="/projects">{STUDIO_VOCAB.projects}</Link>.
        </p>
        <TechnicalDetails summary="Technical — on-disk draft location">
          <p className="forge-support" style={{ margin: 0 }}>
            Session files are written under <code className="le-mono">.lenses-local/</code> on the server—gitignored
            workspace data.
          </p>
        </TechnicalDetails>
      </header>

      {wizardDisabled ? (
        <StatePanel
          variant="not_configured"
          title="Blueprints Wizard is turned off here"
          description="This Lenses server does not expose the wizard API. Ask your operator to enable it if your team should use guided Blueprints sessions."
          assistShortcuts={{ context: 'Blueprints Wizard' }}
          aiRecovery={{
            prompt:
              'Blueprints Wizard is disabled on my Lenses server. What configuration enables it and what are the security considerations?',
            label: 'Ask Chat about enabling the wizard',
          }}
          actions={
            <>
              <Link className="le-btn le-btn--primary" to="/plan">
                {STUDIO_VOCAB.planSummary}
              </Link>
              <Link className="le-btn" to="/tutorials">
                Tutorials
              </Link>
            </>
          }
          technicalDetail="Wizard API is disabled on the server."
          telemetryTag="wizard_hub_disabled"
        />
      ) : null}

      {fetchFailure ? (
        <StatePanel
          variant="unavailable"
          title={fetchFailure.title}
          description={fetchFailure.description}
          technicalDetail={fetchFailure.technical}
          assistShortcuts={{ context: 'Blueprints Wizard' }}
          actions={
            <button type="button" className="le-btn le-btn--primary" onClick={() => load(false)} disabled={refreshing}>
              Retry
            </button>
          }
          telemetryTag="wizard_hub_fetch_failed"
        />
      ) : null}

      {createFailure ? (
        <StatePanel
          variant="unavailable"
          title={createFailure.title}
          description={createFailure.description}
          technicalDetail={createFailure.technical}
          density="compact"
          actions={
            <button type="button" className="le-btn" onClick={() => setCreateFailure(null)}>
              Dismiss
            </button>
          }
        />
      ) : null}

      {!blocked ? (
        <div
          className="ks-wizard-flow__hub-actions"
          style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'center' }}
          aria-busy={refreshing || creating || undefined}
        >
          <button
            type="button"
            className="le-btn le-btn--primary"
            disabled={creating || refreshing}
            onClick={onNew}
          >
            {creating ? 'Starting…' : 'New session'}
          </button>
          <button type="button" className="le-btn" disabled={refreshing || creating} onClick={() => load(true)}>
            {refreshing ? 'Refreshing…' : 'Refresh list'}
          </button>
          {(refreshing || creating) && (
            <span className="forge-support ks-wizard-flow__muted" aria-live="polite">
              {creating ? 'Creating session…' : 'Updating session list…'}
            </span>
          )}
        </div>
      ) : null}

      {!blocked ? (
        <ul className="ks-wizard-flow__session-list" style={{ marginTop: '1rem' }}>
          {(sessions ?? []).map((s) => (
            <li key={s.session_id}>
              <button
                type="button"
                className="ks-wizard-flow__session-item"
                onClick={() => onOpen(s.session_id)}
              >
                <span>
                  <strong>{s.title?.trim() ? s.title : '(untitled)'}</strong>
                  <span className="ks-wizard-flow__session-meta" style={{ marginLeft: '0.5rem' }}>
                    {s.state} · {s.mode}
                  </span>
                </span>
                <span className="ks-wizard-flow__session-meta">
                  step {s.step_index} · {s.updated_at}
                </span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}

      {!blocked && (sessions ?? []).length === 0 ? (
        <StatePanel
          variant="empty"
          title="No wizard sessions yet"
          description={BLUEPRINTS_WIZARD_HUB_COPY.emptySessionsDetail}
          assistShortcuts={{ context: 'Blueprints Wizard' }}
          actions={
            <>
              <button type="button" className="le-btn le-btn--primary" disabled={creating} onClick={onNew}>
                New session
              </button>
              <Link className="le-btn" to="/plan">
                {STUDIO_VOCAB.planSummary}
              </Link>
              <Link className="le-btn" to="/tutorials">
                Tutorials
              </Link>
            </>
          }
          telemetryTag="wizard_hub_empty"
        />
      ) : null}

    </div>
  )
}
