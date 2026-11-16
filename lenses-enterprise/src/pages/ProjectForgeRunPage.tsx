import { useCallback, useMemo, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { useResilientJsonBlock } from '../hooks/useResilientJsonBlock'
import { PageHeader, StatePanel, TechnicalDetails } from '../components/page'
import { ProjectLocalNav } from '../components/projects'
import { chargeMdCandidates } from '../lib/copilotPageEvidence'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'
import {
  ForgeKeyValueGrid,
  ForgeRunHeader,
  type ForgeRunBadge,
} from '../forgesdlc-kitchensink'
import { apiPostJson } from '../api/http'
import { PROJECT_OBJECT_HOME, STUDIO_VOCAB } from '../nav/studioVisibleCopy'

type ForgeRunsListPayload = {
  ok?: boolean
  runs?: { forge_run_id?: string; forge_run?: Record<string, unknown> | null }[]
}

type ForgeRunBundlePayload = {
  ok?: boolean
  bundle?: {
    forge_run_id?: string
    forge_run?: Record<string, unknown> | null
    approvals?: Record<string, unknown>
    evidence_packet?: Record<string, unknown> | null
    local_runner_result?: Record<string, unknown> | null
    follow_on_sparks?: unknown[] | null
    events_tail?: unknown[]
  }
  run_dir?: string
  error?: string
}

export function ProjectForgeRunPage() {
  const { name = '' } = useParams()
  const decoded = decodeURIComponent(name)
  const enc = encodeURIComponent(decoded)
  const [searchParams, setSearchParams] = useSearchParams()
  const runId = (searchParams.get('run_id') || '').trim()
  const [decisionBusy, setDecisionBusy] = useState(false)

  const listUrl = `/api/project/${enc}/forge-runs`
  const bundleUrl = runId ? `/api/project/${enc}/forge-runs?run_id=${encodeURIComponent(runId)}` : listUrl

  const copilotEvidence = useMemo(
    () => ({
      pageContextSummary: decoded
        ? `Forge Studio · ${STUDIO_VOCAB.forgePlatformRun} · ${decoded}`
        : `Forge Studio · ${STUDIO_VOCAB.forgePlatformRun}`,
      relatedMdRelPaths: chargeMdCandidates(decoded || undefined),
    }),
    [decoded],
  )
  useLensesCopilotPage({
    route: 'projects',
    projectSlug: decoded || undefined,
    scopeSite: decoded || undefined,
    pageContextSummary: copilotEvidence.pageContextSummary,
    relatedMdRelPaths: copilotEvidence.relatedMdRelPaths,
  })

  const listBundle = useResilientJsonBlock<ForgeRunsListPayload | ForgeRunBundlePayload>(bundleUrl, {
    snapshotKey: `project-forge-runs:${decoded}:${runId || 'list'}`,
  })

  const setRunId = useCallback(
    (id: string) => {
      const next = new URLSearchParams(searchParams)
      if (id) next.set('run_id', id)
      else next.delete('run_id')
      setSearchParams(next, { replace: true })
    },
    [searchParams, setSearchParams],
  )

  const onDecision = async (state: string) => {
    if (!runId) return
    setDecisionBusy(true)
    try {
      await apiPostJson(`/api/project/${enc}/forge-run-decision`, {
        forge_run_id: runId,
        state,
      })
      listBundle.retry()
    } finally {
      setDecisionBusy(false)
    }
  }

  const data = listBundle.data
  const isList = !!(data && 'runs' in data && !runId)
  const bundle = data && 'bundle' in data ? (data as ForgeRunBundlePayload).bundle : undefined
  const fr = (bundle?.forge_run || null) as Record<string, unknown> | null
  const intent = (fr?.intent || {}) as Record<string, unknown>
  const title = typeof intent.summary === 'string' ? intent.summary : runId || STUDIO_VOCAB.forgePlatformRun
  const evidence = (fr?.evidence || {}) as Record<string, unknown>
  const dec = (fr?.decision || {}) as Record<string, unknown>
  const badges: ForgeRunBadge[] = []
  const est = evidence.status
  if (typeof est === 'string')
    badges.push({ label: est, tone: est === 'passed' ? 'success' : 'warning' })
  const dst = dec.state
  if (typeof dst === 'string') badges.push({ label: dst, tone: 'neutral' })

  return (
    <>
      <PageHeader
        title={`${decoded} · ${STUDIO_VOCAB.forgePlatformRun}`}
        preface={
          <Link to={`/projects/${enc}`} className="forge-support">
            ← {STUDIO_VOCAB.projectDashboard}
          </Link>
        }
        subtitle={<>{PROJECT_OBJECT_HOME.forgeRunPageLead}</>}
      />
      <ProjectLocalNav projectName={decoded} />
      <section className="le-stack" style={{ marginTop: '1rem' }}>
        <TechnicalDetails summary="Run selection" defaultOpen>
          <div className="le-stack">
          <p className="le-muted">
            Reads <code>.forge/runs/</code> in this repository. Seed from{' '}
            <code>sprints/selfhost-alpha/fixtures/</code> in forge-platform, then run{' '}
            <code>selfhost_runner.py</code> / <code>selfhost_import_evidence.py</code>.
          </p>
          {!runId && data && 'runs' in data ? (
            <ul className="le-list">
              {(((data as ForgeRunsListPayload).runs) || []).map((r) => (
                <li key={r.forge_run_id}>
                  <button type="button" className="le-btn le-btn--small" onClick={() => setRunId(r.forge_run_id || '')}>
                    Open {r.forge_run_id}
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
          {runId ? (
            <p>
              <button type="button" className="le-btn le-btn--small" onClick={() => setRunId('')}>
                Back to list
              </button>
            </p>
          ) : null}
          </div>
        </TechnicalDetails>

        {listBundle.failure ? (
          <StatePanel
            variant="error"
            title="Load error"
            technicalDetail={listBundle.failure.summary}
          />
        ) : null}

        {bundle && fr ? (
          <>
            <ForgeRunHeader title={title} subtitle={runId} badges={badges} />
            <ForgeKeyValueGrid
              items={[
                { label: 'forge_run_id', value: String(fr.forge_run_id ?? runId) },
                {
                  label: 'evidence (packet) status',
                  value: String((bundle.evidence_packet as Record<string, unknown> | null)?.evidence
                    ? ((bundle.evidence_packet as Record<string, unknown>).evidence as Record<string, unknown>)
                        ?.status ?? '—'
                    : '—'),
                },
                {
                  label: 'local runner',
                  value: bundle.local_runner_result
                    ? String((bundle.local_runner_result as Record<string, unknown>).summary ?? '…')
                    : '—',
                },
              ]}
            />
            <TechnicalDetails summary="Approval requests" defaultOpen>
              <pre className="le-pre">
                {JSON.stringify(bundle.approvals || {}, null, 2)}
              </pre>
            </TechnicalDetails>
            <TechnicalDetails summary="Evidence packet (excerpt)" defaultOpen>
              <pre className="le-pre">
                {JSON.stringify(bundle.evidence_packet || {}, null, 2).slice(0, 12000)}
              </pre>
            </TechnicalDetails>
            <TechnicalDetails summary="Follow-on sparks" defaultOpen>
              <pre className="le-pre">
                {JSON.stringify(bundle.follow_on_sparks || [], null, 2)}
              </pre>
            </TechnicalDetails>
            <TechnicalDetails summary="Decision (local JSON write)" defaultOpen>
              <p className="le-muted">
                Loopback or <code>LENSES_ALLOW_ACTIONS</code> required — same safety class as other Studio writes.
              </p>
              <div className="le-btn-row">
                <button
                  type="button"
                  className="le-btn le-btn--small"
                  disabled={decisionBusy}
                  onClick={() => onDecision('approved')}
                >
                  Mark approved
                </button>
                <button
                  type="button"
                  className="le-btn le-btn--small"
                  disabled={decisionBusy}
                  onClick={() => onDecision('rejected')}
                >
                  Mark rejected
                </button>
                <button
                  type="button"
                  className="le-btn le-btn--small"
                  disabled={decisionBusy}
                  onClick={() => onDecision('deferred')}
                >
                  Mark deferred
                </button>
              </div>
            </TechnicalDetails>
            <TechnicalDetails summary="events.ndjson (tail)" defaultOpen>
              <pre className="le-pre">{JSON.stringify(bundle.events_tail || [], null, 2)}</pre>
            </TechnicalDetails>
          </>
        ) : null}

        {isList && (!data || !((data as ForgeRunsListPayload).runs || []).length) ? (
          <StatePanel
            variant="empty"
            title="No runs"
            description="No directories under `.forge/runs/` for this repo."
          />
        ) : null}
      </section>
    </>
  )
}
