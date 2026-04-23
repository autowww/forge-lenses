import { useCallback, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'
import { AdvancedSurfaceFraming, PageHeader, StatePanel, TechnicalDetails } from '../components/page'
import {
  clearStudioTelemetry,
  getShortcutEntryShare,
  getStudioTelemetrySnapshot,
  type StudioTelemetrySnapshot,
} from '../telemetry/studioTelemetry'
import { FlowArtifactsExplainerBody } from '../components/onboarding/FlowArtifactsExplainerBody'
import { blueprintsWizardFeatureEnabled } from '../util/experimentalFlags'
import { flowArtifactsHelpHomeTo } from '../nav/studioHelpQuery'
import {
  ADMIN_INSPECT_COPY,
  ADVANCED_SURFACE_FRAMES,
  ROUTE_SUBTITLE,
  STUDIO_ONBOARDING,
  STUDIO_VOCAB,
} from '../nav/studioVisibleCopy'

function formatJson(s: StudioTelemetrySnapshot) {
  return JSON.stringify(s, null, 2)
}

export function UxInsightsPage() {
  useLensesCopilotPage({ route: 'ux-insights', defaultQuery: ADMIN_INSPECT_COPY.copilotUxDiagnostics })
  const [snap, setSnap] = useState(() => getStudioTelemetrySnapshot())
  const shortcutShare = useMemo(() => getShortcutEntryShare(snap), [snap])

  const refresh = useCallback(() => {
    setSnap(getStudioTelemetrySnapshot())
  }, [])

  const onClear = useCallback(() => {
    clearStudioTelemetry()
    setSnap(getStudioTelemetrySnapshot())
  }, [])

  const onCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(formatJson(snap))
    } catch {
      /* ignore */
    }
  }, [snap])

  const topRoutes = useMemo(() => {
    const entries = Object.entries(snap.aggregates.routeViews).sort((a, b) => b[1] - a[1])
    return entries.slice(0, 18)
  }, [snap])

  const topPanels = useMemo(() => {
    const entries = Object.entries(snap.aggregates.statePanels).sort((a, b) => b[1] - a[1])
    return entries.slice(0, 14)
  }, [snap])

  const topCommandBar = useMemo(() => {
    const entries = Object.entries(snap.aggregates.commandBarActions).sort((a, b) => b[1] - a[1])
    return entries.slice(0, 20)
  }, [snap])

  const topAskFails = useMemo(() => {
    const entries = Object.entries(snap.aggregates.commandBarAskFailures).sort((a, b) => b[1] - a[1])
    return entries.slice(0, 14)
  }, [snap])

  return (
    <>
      <PageHeader
        title={STUDIO_VOCAB.uxInsights}
        subtitle={ROUTE_SUBTITLE.uxInsights}
        preface={
          <Link to="/" className="forge-support">
            ← {STUDIO_VOCAB.overview}
          </Link>
        }
        actions={
          <>
            <button type="button" className="le-btn le-btn--small" onClick={refresh}>
              Refresh
            </button>
            <button type="button" className="le-btn le-btn--small" onClick={onCopy}>
              Copy JSON
            </button>
            <button type="button" className="le-btn le-btn--small" onClick={onClear}>
              Clear buffer
            </button>
          </>
        }
      />
      <div style={{ marginTop: '-0.35rem', marginBottom: '0.75rem' }}>
        <AdvancedSurfaceFraming frame={ADVANCED_SURFACE_FRAMES.uxDiagnostics} />
      </div>
      <section className="le-panel" style={{ marginBottom: '1rem' }}>
        <h2 className="le-panel__title" style={{ fontSize: '0.95rem' }}>
          Studio layout (Flow vs Artifacts)
        </h2>
        <p className="forge-support" style={{ fontSize: '0.82rem', lineHeight: 1.5, marginBottom: '0.65rem' }}>
          {STUDIO_ONBOARDING.uxInsightsHelpLead}
        </p>
        <p style={{ marginBottom: '0.55rem' }}>
          <Link className="le-btn le-btn--small le-btn--primary" to={flowArtifactsHelpHomeTo()}>
            Open explainer on overview
          </Link>
        </p>
        <details className="le-raw-wrap">
          <summary>Show full explanation here</summary>
          <div className="le-fa-onboarding__panel le-fa-onboarding__panel--embedded">
            <FlowArtifactsExplainerBody density="compact" />
          </div>
        </details>
      </section>

      <StatePanel
        variant="stale"
        density="compact"
        title="Local-only diagnostics"
        description="Counts and events stay in this browser tab (in-memory). They reset on full reload unless you export."
      />
      <div style={{ marginBottom: '1rem' }}>
        <TechnicalDetails summary="Developer console hook (inspect)" className="forge-support">
          <p style={{ margin: 0, fontSize: '0.85rem' }}>
            Optional console detail:{' '}
            <code className="le-mono">localStorage.setItem(&apos;lenses_studio_telemetry_console&apos;,&apos;1&apos;)</code>{' '}
            then refresh. Disable: set to <code className="le-mono">&apos;0&apos;</code> in dev.
          </p>
        </TechnicalDetails>
      </div>

      <section className="le-panel" style={{ marginBottom: '1rem' }}>
        <h2 className="le-panel__title" style={{ fontSize: '0.95rem' }}>
          Scorecard (session)
        </h2>
        <ul className="le-list" style={{ fontSize: '0.85rem', lineHeight: 1.5 }}>
          <li>
            <strong>Shortcut sidebar share:</strong>{' '}
            {shortcutShare == null ? '— (no sidebar clicks yet)' : `${(shortcutShare * 100).toFixed(1)}%`}
          </li>
          <li>
            <strong>Distinct routes seen:</strong> {Object.keys(snap.aggregates.routeViews).length}
          </li>
          <li>
            <strong>State panels (non-loading) recorded:</strong>{' '}
            {Object.values(snap.aggregates.statePanels).reduce((a, b) => a + b, 0)}
          </li>
          <li>
            <strong>Page failures recorded:</strong>{' '}
            {Object.values(snap.aggregates.pageFailures).reduce((a, b) => a + b, 0)}
          </li>
          <li>
            <strong>Command bar actions:</strong>{' '}
            {Object.values(snap.aggregates.commandBarActions).reduce((a, b) => a + b, 0)}
          </li>
          <li>
            <strong>Command bar Ask failures (distinct queries):</strong>{' '}
            {Object.keys(snap.aggregates.commandBarAskFailures).length}
          </li>
        </ul>
      </section>

      <section className="le-panel" style={{ marginBottom: '1rem' }}>
        <h2 className="le-panel__title" style={{ fontSize: '0.95rem' }}>
          Command bar (Find / Ask / Do)
        </h2>
        {topCommandBar.length === 0 ? (
          <p className="forge-support">Open the command bar (⌘K / Ctrl+K) to emit events.</p>
        ) : (
          <ul className="le-list" style={{ fontSize: '0.82rem' }}>
            {topCommandBar.map(([k, v]) => (
              <li key={k}>
                <code className="le-mono">{k}</code> — {v}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="le-panel" style={{ marginBottom: '1rem' }}>
        <h2 className="le-panel__title" style={{ fontSize: '0.95rem' }}>
          Command bar — failed Ask queries (rolling)
        </h2>
        {topAskFails.length === 0 ? (
          <p className="forge-support">No failed Ask turns recorded yet.</p>
        ) : (
          <ul className="le-list" style={{ fontSize: '0.78rem' }}>
            {topAskFails.map(([q, n]) => (
              <li key={q}>
                <span style={{ wordBreak: 'break-word' }}>{q}</span> — {n}×
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="le-panel" style={{ marginBottom: '1rem' }}>
        <h2 className="le-panel__title" style={{ fontSize: '0.95rem' }}>
          Top routes (pathname)
        </h2>
        {topRoutes.length === 0 ? (
          <p className="forge-support">Navigate the app to populate route_view events.</p>
        ) : (
          <ul className="le-list" style={{ fontSize: '0.82rem' }}>
            {topRoutes.map(([path, n]) => (
              <li key={path}>
                <code className="le-mono">{path}</code> — {n}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="le-panel" style={{ marginBottom: '1rem' }}>
        <h2 className="le-panel__title" style={{ fontSize: '0.95rem' }}>
          Sidebar intent clicks
        </h2>
        <ul className="le-list" style={{ fontSize: '0.82rem' }}>
          {Object.entries(snap.aggregates.sidebarNavByIntent).map(([k, v]) => (
            <li key={k}>
              <strong>{k}</strong>: {v}
            </li>
          ))}
        </ul>
      </section>

      <section className="le-panel" style={{ marginBottom: '1rem' }}>
        <h2 className="le-panel__title" style={{ fontSize: '0.95rem' }}>
          State panels (variant:tag)
        </h2>
        {topPanels.length === 0 ? (
          <p className="forge-support">Empty/error panels with telemetryTag increment here.</p>
        ) : (
          <ul className="le-list" style={{ fontSize: '0.82rem' }}>
            {topPanels.map(([k, v]) => (
              <li key={k}>
                <code className="le-mono">{k}</code> — {v}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="le-panel" style={{ marginBottom: '1rem' }}>
        <h2 className="le-panel__title" style={{ fontSize: '0.95rem' }}>
          {ADMIN_INSPECT_COPY.settingsSectionLabs}
        </h2>
        <p className="forge-support" style={{ fontSize: '0.82rem', marginTop: 0 }}>
          Not listed in primary side navigation — bookmark or use from here for QA and demos.
        </p>
        <ul className="le-list" style={{ fontSize: '0.88rem', lineHeight: 1.55 }}>
          <li>
            <Link to="/feature-showcase">{STUDIO_VOCAB.featureShowcase} (lab)</Link>
          </li>
          <li>
            <Link to="/view/local-site/">Site preview (empty path lab)</Link>
          </li>
          <li>
            <Link to={flowArtifactsHelpHomeTo()}>{STUDIO_ONBOARDING.flowArtifactsChipLabel} (overview deep link)</Link>
          </li>
          {blueprintsWizardFeatureEnabled() ? (
            <li>
              <Link to="/blueprints/wizard/session/probe">Blueprints Wizard session (probe)</Link>
            </li>
          ) : null}
        </ul>
      </section>

      <TechnicalDetails summary="Recent events (raw JSON)">
        <pre className="le-preview le-json" style={{ maxHeight: '18rem', fontSize: '0.75rem', margin: 0 }}>
          {formatJson({ ...snap, events: snap.events.slice(-40) })}
        </pre>
      </TechnicalDetails>
    </>
  )
}
