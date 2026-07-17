import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { apiGetJson } from '../api/http'
import { PageHeader, StatePanel } from '../components/page'
import { FoundryApprovalBar } from '../components/foundry/FoundryApprovalBar'
import { FoundryAssayCard } from '../components/foundry/FoundryAssayCard'
import { FoundryDiffReview } from '../components/foundry/FoundryDiffReview'
import { FoundryLiveRunPanel } from '../components/foundry/FoundryLiveRunPanel'
import { FoundryPhaseDetails } from '../components/foundry/FoundryPhaseDetails'
import '../components/foundry/foundry-review.css'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'
import {
  ForgeRunHeader,
  ForgeWorkflowStageBar,
  type ForgeRunBadge,
} from '../forgesdlc-kitchensink'
import { apiPostJson } from '../api/http'
import type { FoundryRun } from '../lib/foundryTypes'
import { foundryStagesWithPulse } from '../lib/foundryActivity'
import { ROUTE_SUBTITLE, STUDIO_VOCAB, WORK_COPILOT_DEFAULT_PLAN } from '../nav/studioVisibleCopy'

export function FoundryRunPage() {
  const { runId = '' } = useParams()
  const decoded = decodeURIComponent(runId)
  const [run, setRun] = useState<FoundryRun | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedPhaseId, setSelectedPhaseId] = useState<string | null>(null)

  useLensesCopilotPage({
    route: 'work',
    pageContextSummary: `Foundry run ${decoded}`,
    defaultQuery: WORK_COPILOT_DEFAULT_PLAN,
  })

  const fetchRun = useCallback(async () => {
    if (!decoded) return
    try {
      const data = await apiGetJson<FoundryRun>(`/api/foundry/runs/${encodeURIComponent(decoded)}`)
      setRun(data)
      setError(null)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load run')
    } finally {
      setLoading(false)
    }
  }, [decoded])

  useEffect(() => {
    void fetchRun()
  }, [fetchRun])

  useEffect(() => {
    if (!run || (run.status !== 'running' && run.status !== 'pending')) return
    const t = window.setInterval(() => void fetchRun(), 1000)
    return () => window.clearInterval(t)
  }, [run, fetchRun])

  const badges: ForgeRunBadge[] = useMemo(() => {
    const out: ForgeRunBadge[] = []
    if (run?.level) out.push({ label: run.level, tone: 'neutral' })
    if (run?.status) {
      const tone =
        run.status === 'completed' ? 'success' : run.status === 'failed' ? 'warning' : 'neutral'
      out.push({ label: run.status, tone })
    }
    if (run?.execution_mode) out.push({ label: run.execution_mode, tone: 'neutral' })
    return out
  }, [run])

  const stages = useMemo(
    () =>
      foundryStagesWithPulse(run?.phases, run?.status, run?.current_phase).map((p) => ({
        id: p.id,
        label: p.label,
        status: p.status,
      })),
    [run?.phases, run?.status, run?.current_phase],
  )

  const onApprove = async (confirm: boolean) => {
    await apiPostJson(`/api/foundry/runs/${encodeURIComponent(decoded)}/approve`, {
      confirm_human_approval: confirm,
    })
    await fetchRun()
  }

  const showApproval =
    run?.status === 'completed' && run.assay_ok === true && !run.promoted && !run.approved

  const showReview = run?.status === 'completed' || run?.status === 'failed' || run?.promoted

  return (
    <>
      <PageHeader
        title={STUDIO_VOCAB.foundryRun}
        preface={
          <Link to="/foundry" className="forge-support">
            ← {STUDIO_VOCAB.foundry}
          </Link>
        }
        subtitle={<>{ROUTE_SUBTITLE.foundryRun}</>}
      />
      {loading ? (
        <StatePanel variant="loading" title="Loading run" />
      ) : error ? (
        <StatePanel variant="error" title="Load error" technicalDetail={error} />
      ) : !run?.id ? (
        <StatePanel variant="empty" title="Run not found" description={`No run ${decoded}`} />
      ) : (
        <section className="le-stack" style={{ marginTop: '1rem' }}>
          <ForgeRunHeader title={run.goal ?? decoded} subtitle={run.target} badges={badges} />
          <ForgeWorkflowStageBar
            stages={stages}
            aria-label="Dark Factory workflow stages"
            currentStageId={selectedPhaseId ?? run.current_phase ?? null}
            onStageClick={setSelectedPhaseId}
          />
          <FoundryLiveRunPanel run={run} />
          <FoundryPhaseDetails
            phases={run.phases ?? []}
            selectedId={selectedPhaseId}
            onSelect={setSelectedPhaseId}
          />
          {run.status === 'completed' || run.status === 'failed' ? <FoundryAssayCard run={run} /> : null}
          {showReview ? <FoundryDiffReview review={run.review} /> : null}
          {showApproval ? (
            <FoundryApprovalBar runId={decoded} onApprove={onApprove} />
          ) : run.promoted ? (
            <StatePanel
              variant="empty"
              title="Promoted"
              description="Changed files were copied to the target repo. Review the git diff above, then commit on a feature branch and open a PR."
            />
          ) : null}
        </section>
      )}
    </>
  )
}
