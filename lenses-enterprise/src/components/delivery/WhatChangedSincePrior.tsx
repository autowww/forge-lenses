import { useEffect, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { StatePanel, TechnicalDetails } from '../page'
import { useWorkspace } from '../../context/WorkspaceContext'
import { useResilientJsonBlock } from '../../hooks/useResilientJsonBlock'
import { STUDIO_VOCAB } from '../../nav/studioVisibleCopy'
import { recordPageFailure } from '../../telemetry/studioTelemetry'
import type { CicdControlTowerPayload } from './DeliveryControlTowerCard'

/** MVP: no server-side yesterday snapshot; links + CI/CD posture strip for operational context. */
export function WhatChangedSincePrior() {
  const { state } = useWorkspace()
  const refreshKey = state?.resolved_at ?? null
  const cicd = useResilientJsonBlock<CicdControlTowerPayload>('/api/cicd/control-tower', {
    snapshotKey: 'cicd-control-tower',
    refreshKey,
  })

  useEffect(() => {
    if (cicd.phase === 'error' && cicd.failure) {
      recordPageFailure('cicd_control_tower_what_changed', cicd.failure.summary)
    }
  }, [cicd.phase, cicd.failure])

  let posture: ReactNode = null
  const d = cicd.data
  if (cicd.phase === 'loading' && !d) {
    posture = <p className="forge-support">Loading release posture…</p>
  } else if (d?.ok && d.feature_enabled !== false && d.provider_kind === 'local_fixture') {
    const blocked = (d.blocked_promotions ?? []).length
    const freezes = (d.freeze_windows ?? []).filter((f) => f.active).length
    const focus = d.release_train?.current_focus
    const envn = (d.environments ?? []).length
    posture = (
      <p className="forge-support" style={{ marginTop: 0 }}>
        <strong>Release posture:</strong> {envn} environment(s) in fixture
        {focus ? (
          <>
            {' '}
            · train focus <code className="le-mono">{focus}</code>
          </>
        ) : null}
        {freezes ? <> · {freezes} active freeze(s)</> : null}
        {blocked ? <> · {blocked} blocked promotion(s)</> : null}
        {' · '}
        <a className="le-delivery-link" href="#le-cicd-tower">
          Open CI/CD control tower
        </a>
      </p>
    )
  } else if (d?.ok && d.feature_enabled === false) {
    posture = (
      <StatePanel
        variant="empty"
        density="compact"
        title="CI/CD tower off"
        description="Enable LENSES_EXPERIMENTAL_CICD_ORCHESTRATION for environment and promotion summaries here."
      />
    )
  } else if (d?.ok && d.provider_kind === 'scan_only') {
    posture = (
      <p className="forge-support" style={{ marginTop: 0 }}>
        Add <code className="le-mono">cicd-orchestration.json</code> or demo seed to see release posture in this strip.{' '}
        <a className="le-delivery-link" href="#le-cicd-tower">
          Control tower
        </a>
      </p>
    )
  }

  return (
    <section className="le-delivery-section" aria-labelledby="le-delivery-changed-h">
      <h2 id="le-delivery-changed-h" className="le-delivery-section__title">
        What changed since yesterday
      </h2>
      <p className="le-delivery-section__lead">
        A point-in-time compare needs a saved snapshot (not in the API yet). Use workspace activity charts
        for recent delivery pulse, or review charge history in the full workspace UI.
      </p>
      {posture}
      <TechnicalDetails summary="Inspect: charts and delivery JSON endpoints">
        <p className="forge-support" style={{ margin: 0, fontSize: '0.88rem' }}>
          <Link className="le-delivery-link" to="/overview/charts">
            {STUDIO_VOCAB.advancedReporting}
          </Link>
          {' · '}
          <a className="le-delivery-link" href="/api/today-charge">
            Today-charge API
          </a>{' '}
          (same scope when WBS is selected in the Plan query)
          {' · '}
          <a className="le-delivery-link" href="/api/cicd/control-tower">
            CI/CD control tower JSON
          </a>
        </p>
      </TechnicalDetails>
    </section>
  )
}
