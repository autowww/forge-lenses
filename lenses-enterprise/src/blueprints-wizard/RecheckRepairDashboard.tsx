/**
 * Step 10 — Recheck / Repair: structured status report and targeted repair actions.
 */

import { useCallback, useMemo, useState } from 'react'
import type {
  ArtifactReviewApiAction,
  ArtifactSliceKey,
  RecheckReportJson,
  RecheckSummaryJson,
  RunPlanJson,
  RunPlanStepJson,
} from './wizardDomainTypes'
import { ARTIFACT_SLICE_KEYS } from './wizardDomainTypes'
import { clampRunPlan, emptyRunPlanPayload } from './runPlanStep'

function labelChipClass(label: string): string {
  const base = 'le-mono'
  switch (label) {
    case 'present':
    case 'approved':
      return `${base} forge-support`
    case 'missing':
    case 'blocked':
      return `${base} forge-support`
    case 'stale':
    case 'conflicting':
      return `${base} forge-support`
    default:
      return `${base} forge-support`
  }
}

function buildRepairRunPlan(report: RecheckReportJson | undefined, selected: Set<string>): RunPlanJson {
  const rec = report?.recommendations
  const steps: RunPlanStepJson[] = []
  let n = 0
  const add = (title: string, detail: string) => {
    steps.push({
      id: `repair-${n++}`,
      title: title.slice(0, 500),
      detail: detail.slice(0, 8000),
    })
  }
  if (rec) {
    for (const k of rec.approve_first) {
      if (selected.has(k)) add(`Approve upstream: ${k}`, '')
    }
    for (const k of rec.regenerate_keys) {
      if (selected.has(k)) add(`Regenerate: ${k}`, '')
    }
    for (const k of rec.unlock_or_request_changes) {
      if (selected.has(k)) add(`Unlock or request changes: ${k}`, '')
    }
  }
  if (steps.length === 0) {
    return emptyRunPlanPayload()
  }
  return clampRunPlan({
    id: 'recheck-repair-plan',
    title: 'Recheck repair plan',
    steps,
  })
}

export type RecheckRepairDashboardProps = {
  recheckSummary: RecheckSummaryJson | null
  onArtifactRecheck?: () => void
  /** Optional: `POST artifact-recheck` with `dry_run: true` — updates in-memory `recheck_summary` only. */
  onArtifactRecheckPreview?: () => void
  /** True while either persist or preview request is in flight (disables both buttons). */
  recheckBusy?: boolean
  recheckPersistBusy?: boolean
  recheckPreviewBusy?: boolean
  disabled?: boolean
  artifactGenBusy?: boolean
  artifactGenError?: string | null
  onRegenerateKeys: (keys: ArtifactSliceKey[]) => void
  onArtifactReview: (action: ArtifactReviewApiAction, key: ArtifactSliceKey) => void
  onApplyToScope: (notes: string) => void
  onApplyRunPlan: (plan: RunPlanJson) => void
  onJumpToStep: (stepIndex: number) => void
}

export function RecheckRepairDashboard({
  recheckSummary,
  onArtifactRecheck,
  onArtifactRecheckPreview,
  recheckBusy = false,
  recheckPersistBusy = false,
  recheckPreviewBusy = false,
  disabled = false,
  artifactGenBusy = false,
  artifactGenError = null,
  onRegenerateKeys,
  onArtifactReview,
  onApplyToScope,
  onApplyRunPlan,
  onJumpToStep,
}: RecheckRepairDashboardProps) {
  const report = recheckSummary?.report
  const [selected, setSelected] = useState<Set<string>>(() => new Set())

  const recommendedUnion = useMemo(() => {
    const rec = report?.recommendations
    if (!rec) return new Set<string>()
    const u = new Set<string>()
    for (const x of rec.regenerate_keys) u.add(x)
    for (const x of rec.approve_first) u.add(x)
    for (const x of rec.unlock_or_request_changes) u.add(x)
    return u
  }, [report])

  const toggle = useCallback((key: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }, [])

  const selectAllRecommended = useCallback(() => {
    setSelected(new Set(recommendedUnion))
  }, [recommendedUnion])

  const clearSelection = useCallback(() => setSelected(new Set()), [])

  const selectedList = useMemo(
    () => ARTIFACT_SLICE_KEYS.filter((k) => selected.has(k)) as ArtifactSliceKey[],
    [selected],
  )

  const onRegenerate = useCallback(() => {
    if (selectedList.length === 0) return
    onRegenerateKeys(selectedList)
  }, [onRegenerateKeys, selectedList])

  const onUnlockSelected = useCallback(() => {
    for (const k of selectedList) {
      onArtifactReview('unlock', k)
    }
  }, [onArtifactReview, selectedList])

  const onFlagConflicts = useCallback(() => {
    const notes = (report?.recommendations.flag_for_review ?? []).join('\n')
    onApplyToScope(notes)
  }, [onApplyToScope, report])

  const onCreateRunPlan = useCallback(() => {
    const plan = buildRepairRunPlan(report, selected)
    if (plan.steps.length === 0) return
    onApplyRunPlan(plan)
  }, [onApplyRunPlan, report, selected])

  return (
    <section className="forge-support" aria-labelledby="bpw-recheck-heading">
      <h2 id="bpw-recheck-heading" className="forge-support" style={{ fontSize: '1.15rem', fontWeight: 600 }}>
        Recheck / Repair
      </h2>
      <p className="forge-support" style={{ marginTop: '0.35rem', maxWidth: '52rem' }}>
        Deterministic status across artifact slices (planning / engineering / execution). Select keys below, then run
        targeted regeneration, review actions, or apply findings to Scope and Run Plan.
      </p>

      <div style={{ marginTop: '0.75rem', display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'center' }}>
        <button
          type="button"
          className="le-btn le-btn--primary"
          disabled={disabled || recheckBusy || !onArtifactRecheck}
          onClick={() => onArtifactRecheck?.()}
        >
          {recheckPersistBusy || (recheckBusy && !recheckPreviewBusy) ? 'Saving recheck…' : 'Refresh recheck'}
        </button>
        {onArtifactRecheckPreview && (
          <button
            type="button"
            className="le-btn"
            disabled={disabled || recheckBusy}
            onClick={() => onArtifactRecheckPreview()}
            title="Computes recheck on the server without saving the session file. Updates this dashboard only."
          >
            {recheckPreviewBusy ? 'Previewing…' : 'Preview recheck (no save)'}
          </button>
        )}
        {recheckSummary && (
          <span className="forge-support le-mono">
            {recheckSummary.passed ? 'Passed' : 'Issues'}{' '}
            {recheckSummary.checked_at ? `· ${recheckSummary.checked_at}` : ''}
          </span>
        )}
      </div>

      {artifactGenError && (
        <p className="forge-support" role="alert" style={{ marginTop: '0.5rem' }}>
          {artifactGenError}
        </p>
      )}

      {report && report.buckets.length > 0 && (
        <div style={{ marginTop: '1rem' }}>
          <h3 className="forge-support" style={{ fontSize: '1rem', fontWeight: 600 }}>
            Stage buckets
          </h3>
          <table className="forge-support" style={{ marginTop: '0.35rem', borderCollapse: 'collapse', width: '100%', maxWidth: '48rem' }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left', padding: '0.25rem 0.5rem' }}>Bucket</th>
                <th style={{ textAlign: 'left', padding: '0.25rem 0.5rem' }}>Worst</th>
                <th style={{ textAlign: 'left', padding: '0.25rem 0.5rem' }}>Slices</th>
              </tr>
            </thead>
            <tbody>
              {report.buckets.map((b) => (
                <tr key={b.id}>
                  <td style={{ padding: '0.25rem 0.5rem' }} className="le-mono">
                    {b.id}
                  </td>
                  <td style={{ padding: '0.25rem 0.5rem' }}>
                    <span className={labelChipClass(b.worst_label)}>{b.worst_label}</span>
                  </td>
                  <td style={{ padding: '0.25rem 0.5rem' }} className="le-mono" title={b.artifact_keys.join(', ')}>
                    {b.artifact_keys.length} keys
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {report && report.artifacts.length > 0 && (
        <div style={{ marginTop: '1rem' }}>
          <h3 className="forge-support" style={{ fontSize: '1rem', fontWeight: 600 }}>
            Artifacts
          </h3>
          <div style={{ marginTop: '0.35rem', maxHeight: '22rem', overflow: 'auto', border: '1px solid var(--le-border, #3334)' }}>
            <table className="forge-support" style={{ borderCollapse: 'collapse', width: '100%', fontSize: '0.9rem' }}>
              <thead>
                <tr style={{ position: 'sticky', top: 0, background: 'var(--le-panel, #1a1a1c)' }}>
                  <th style={{ padding: '0.2rem 0.35rem', width: '2rem' }} />
                  <th style={{ textAlign: 'left', padding: '0.2rem 0.35rem' }}>Key</th>
                  <th style={{ textAlign: 'left', padding: '0.2rem 0.35rem' }}>Status</th>
                  <th style={{ textAlign: 'left', padding: '0.2rem 0.35rem' }}>Gen</th>
                </tr>
              </thead>
              <tbody>
                {report.artifacts.map((row) => (
                  <tr key={row.artifact_key}>
                    <td style={{ padding: '0.2rem 0.35rem' }}>
                      <input
                        type="checkbox"
                        checked={selected.has(row.artifact_key)}
                        onChange={() => toggle(row.artifact_key)}
                        aria-label={`Select ${row.artifact_key}`}
                      />
                    </td>
                    <td style={{ padding: '0.2rem 0.35rem' }} className="le-mono">
                      {row.artifact_key}
                    </td>
                    <td style={{ padding: '0.2rem 0.35rem' }}>
                      <span className={labelChipClass(row.primary_label)}>{row.primary_label}</span>
                    </td>
                    <td style={{ padding: '0.2rem 0.35rem' }} className="le-mono" title={row.created_at}>
                      {row.generation_id ? row.generation_id.slice(0, 12) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ marginTop: '0.5rem', display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
            <button type="button" className="le-btn" disabled={disabled || recommendedUnion.size === 0} onClick={selectAllRecommended}>
              Select all recommended
            </button>
            <button type="button" className="le-btn" disabled={disabled || selected.size === 0} onClick={clearSelection}>
              Clear selection
            </button>
          </div>
        </div>
      )}

      {report && (
        <div style={{ marginTop: '1rem' }}>
          <h3 className="forge-support" style={{ fontSize: '1rem', fontWeight: 600 }}>
            Repair actions
          </h3>
          <div style={{ marginTop: '0.5rem', display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
            <button
              type="button"
              className="le-btn le-btn--primary"
              disabled={disabled || artifactGenBusy || selectedList.length === 0}
              onClick={onRegenerate}
            >
              Regenerate selected
            </button>
            <button type="button" className="le-btn" disabled={disabled || artifactGenBusy || selectedList.length === 0} onClick={onUnlockSelected}>
              Unlock selected
            </button>
            <button
              type="button"
              className="le-btn"
              disabled={disabled || !(report.recommendations.flag_for_review?.length)}
              onClick={onFlagConflicts}
            >
              Flag conflicts for review (scope)
            </button>
            <button type="button" className="le-btn" disabled={disabled || selected.size === 0} onClick={onCreateRunPlan}>
              Create repair run plan
            </button>
          </div>
        </div>
      )}

      {report && (
        <div style={{ marginTop: '1rem' }}>
          <h3 className="forge-support" style={{ fontSize: '1rem', fontWeight: 600 }}>
            Connect to Scope &amp; Run Plan
          </h3>
          <div style={{ marginTop: '0.5rem', display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
            <button
              type="button"
              className="le-btn"
              disabled={disabled}
              onClick={() => {
                const block = [
                  ...report.recommendations.flag_for_review,
                  ...selectedList.map((k) => `Selected: ${k}`),
                ].join('\n')
                onApplyToScope(block)
              }}
            >
              Apply findings to Scope Selection
            </button>
            <button type="button" className="le-btn" disabled={disabled} onClick={() => onJumpToStep(7)}>
              Jump to Scope (step 8)
            </button>
            <button type="button" className="le-btn" disabled={disabled} onClick={() => onJumpToStep(8)}>
              Jump to Run Plan (step 9)
            </button>
          </div>
        </div>
      )}

      {recheckSummary && recheckSummary.issues.length > 0 && (
        <details style={{ marginTop: '1rem' }} className="forge-support">
          <summary>Legacy issue strings ({recheckSummary.issues.length})</summary>
          <ul style={{ marginTop: '0.35rem' }}>
            {recheckSummary.issues.slice(0, 48).map((i) => (
              <li key={i.slice(0, 120)} className="le-mono">
                {i}
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  )
}
