/**
 * Step 9 — Review & Generate: Run Plan preview + generated planning artifacts.
 */

import { useState } from 'react'
import type { RunPlanPreview } from './runPlanPreviewTypes'
import {
  ARTIFACT_SLICE_DISPLAY_LABELS,
  ENGINEERING_ARTIFACT_SLICE_KEYS,
  EXECUTION_ARTIFACT_SLICE_KEYS,
  PLANNING_ARTIFACT_SLICE_KEYS,
  QUALITY_DIMENSIONS,
  type ArtifactGenerationBundle,
  type ArtifactGenerationJson,
  type ArtifactReviewApiAction,
  type ArtifactSliceKey,
  type GeneratedArtifactRecordJson,
  type RecheckSummaryJson,
} from './wizardDomainTypes'

type Props = {
  preview: RunPlanPreview | null
  draftNote: string
  onDraftChange: (value: string) => void
  disabled?: boolean
  artifactGeneration?: ArtifactGenerationJson
  recheckSummary?: RecheckSummaryJson | null
  /** When false (e.g. local-only / no API), hide generate + review actions. */
  reviewGenAvailable?: boolean
  onGenerateArtifacts?: (
    artifactKey: string | null,
    bundle?: ArtifactGenerationBundle,
    artifactKeys?: ArtifactSliceKey[],
  ) => void
  onArtifactReview?: (
    action: ArtifactReviewApiAction,
    artifactKey: ArtifactSliceKey,
    feedback?: string,
  ) => void
  onApproveArtifactBundle?: (artifactKeys: ArtifactSliceKey[]) => void
  onExportArtifacts?: (artifactKeys: ArtifactSliceKey[]) => void
  onArtifactRecheck?: () => void
  artifactGenBusy?: boolean
  recheckBusy?: boolean
  artifactGenError?: string | null
}

function ArtifactCard({
  sliceKey,
  record,
  disabled,
  onGenerate,
  onReview,
  busy,
  selectable,
  selected,
  onToggleSelect,
}: {
  sliceKey: ArtifactSliceKey
  record: GeneratedArtifactRecordJson | undefined
  disabled: boolean
  onGenerate: () => void
  onReview: (action: ArtifactReviewApiAction, feedback?: string) => void
  busy: boolean
  selectable?: boolean
  selected?: boolean
  onToggleSelect?: () => void
}) {
  const [feedbackOpen, setFeedbackOpen] = useState(false)
  const [feedback, setFeedback] = useState('')
  const locked = record?.locked === true
  const title = ARTIFACT_SLICE_DISPLAY_LABELS[sliceKey]
  const content = record?.content as Record<string, unknown> | undefined

  return (
    <div
      style={{
        marginTop: '0.75rem',
        padding: '0.75rem',
        border: '1px solid rgba(255,255,255,0.12)',
        borderRadius: '6px',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.5rem' }}>
        <p className="forge-support" style={{ fontWeight: 600, margin: 0, display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          {selectable ? (
            <input
              type="checkbox"
              checked={selected === true}
              onChange={onToggleSelect}
              disabled={disabled || busy}
              aria-label={`Select ${title}`}
            />
          ) : null}
          {title}
        </p>
        {record && (
          <span className="forge-support" style={{ fontSize: '0.85rem', opacity: 0.9 }}>
            {record.review_status}
            {locked ? ' · locked' : ''}
          </span>
        )}
      </div>

      {record ? (
        <>
          <div className="forge-support" style={{ marginTop: '0.5rem', fontSize: '0.88rem' }}>
            <strong>Quality</strong>
            <ul style={{ margin: '0.35rem 0 0', paddingLeft: '1.1rem' }}>
              {QUALITY_DIMENSIONS.map((dim) => {
                const q = record.quality[dim]
                const score = q?.score ?? 0
                const rat = q?.rationale ?? ''
                return (
                  <li key={dim} style={{ marginBottom: '0.2rem' }}>
                    {dim}: {(score * 100).toFixed(0)}%
                    {rat ? ` — ${rat}` : ''}
                  </li>
                )
              })}
            </ul>
          </div>
          {sliceKey === 'foundation_brief_final' && typeof content?.markdown === 'string' && (
            <pre
              className="forge-support"
              style={{
                marginTop: '0.5rem',
                maxHeight: '12rem',
                overflow: 'auto',
                whiteSpace: 'pre-wrap',
                fontSize: '0.82rem',
                padding: '0.5rem',
                background: 'rgba(0,0,0,0.2)',
                borderRadius: '4px',
              }}
            >
              {String(content.markdown)}
            </pre>
          )}
          {sliceKey === 'assumptions_ledger' && Array.isArray(content?.entries) && (
            <ul className="forge-support" style={{ fontSize: '0.85rem', marginTop: '0.35rem' }}>
              {(content.entries as { id?: string; text?: string }[]).map((e) => (
                <li key={e.id ?? e.text}>{e.text}</li>
              ))}
            </ul>
          )}
          {sliceKey !== 'foundation_brief_final' &&
            sliceKey !== 'assumptions_ledger' &&
            content && (
            <pre
              className="forge-support"
              style={{
                marginTop: '0.5rem',
                maxHeight: '10rem',
                overflow: 'auto',
                fontSize: '0.78rem',
                whiteSpace: 'pre-wrap',
              }}
            >
              {JSON.stringify(content, null, 2)}
            </pre>
          )}
          <p className="forge-support" style={{ fontSize: '0.8rem', opacity: 0.85, marginTop: '0.35rem' }}>
            Model: {record.provenance.model || '—'} · id: {record.provenance.generation_id.slice(0, 12)}…
            {record.provenance.lineage?.upstream?.length ? (
              <span>
                {' '}
                · lineage: {record.provenance.lineage.upstream.length} upstream
              </span>
            ) : null}
          </p>
          {record.feedback ? (
            <p className="forge-support" style={{ fontSize: '0.85rem', marginTop: '0.35rem' }}>
              Feedback: {record.feedback}
            </p>
          ) : null}
        </>
      ) : (
        <p className="forge-support" style={{ marginTop: '0.5rem', opacity: 0.85 }}>
          Not generated yet.
        </p>
      )}

      <div style={{ marginTop: '0.65rem', display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>
        <button
          type="button"
          className="forge-support"
          disabled={disabled || busy || locked}
          onClick={onGenerate}
        >
          {record ? 'Regenerate section' : 'Generate'}
        </button>
        <button
          type="button"
          className="forge-support"
          disabled={disabled || busy || !record || locked}
          onClick={() => onReview('approve')}
        >
          Approve
        </button>
        {!feedbackOpen ? (
          <button
            type="button"
            className="forge-support"
            disabled={disabled || busy || !record || locked}
            onClick={() => setFeedbackOpen(true)}
          >
            Request changes
          </button>
        ) : (
          <>
            <textarea
              className="le-input"
              style={{ width: '100%', minHeight: '3rem', marginTop: '0.25rem' }}
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder="What should change?"
            />
            <button
              type="button"
              className="forge-support"
              disabled={disabled || busy}
              onClick={() => {
                onReview('request_changes', feedback)
                setFeedbackOpen(false)
                setFeedback('')
              }}
            >
              Submit feedback
            </button>
            <button type="button" className="forge-support" onClick={() => setFeedbackOpen(false)}>
              Cancel
            </button>
          </>
        )}
        <button
          type="button"
          className="forge-support"
          disabled={disabled || busy || !record || locked}
          onClick={() => onReview('lock')}
        >
          Lock
        </button>
        {locked ? (
          <button
            type="button"
            className="forge-support"
            disabled={disabled || busy}
            onClick={() => onReview('unlock')}
          >
            Unlock
          </button>
        ) : null}
      </div>
    </div>
  )
}

export function ReviewGenerateStepPanel({
  preview,
  draftNote,
  onDraftChange,
  disabled = false,
  artifactGeneration,
  recheckSummary = null,
  reviewGenAvailable = true,
  onGenerateArtifacts,
  onArtifactReview,
  onApproveArtifactBundle,
  onExportArtifacts,
  onArtifactRecheck,
  artifactGenBusy = false,
  recheckBusy = false,
  artifactGenError = null,
}: Props) {
  const ag = artifactGeneration ?? { schema_version: 2, artifacts: {} }
  const arts = ag.artifacts ?? {}
  const [selectedKeys, setSelectedKeys] = useState<Set<ArtifactSliceKey>>(new Set())

  const toggleKey = (k: ArtifactSliceKey) => {
    setSelectedKeys((prev) => {
      const n = new Set(prev)
      if (n.has(k)) n.delete(k)
      else n.add(k)
      return n
    })
  }

  const selectedList = (): ArtifactSliceKey[] => Array.from(selectedKeys)

  return (
    <div className="forge-support">
      <p className="forge-support" style={{ marginTop: '0.5rem', lineHeight: 1.5 }}>
        Saving the session from this step onward materializes the output pack into{' '}
        <strong>wizard_domain.artifact_packs</strong>: new and updated lines become <strong>draft</strong> rows for
        downstream work; rows classified as <strong>untouched</strong> in the Run Plan preview keep their existing ids
        and status (e.g. ready).
      </p>
      {preview ? (
        <div
          style={{
            marginTop: '0.75rem',
            padding: '0.75rem',
            border: '1px solid rgba(255,255,255,0.12)',
            borderRadius: '6px',
          }}
        >
          <p className="forge-support" style={{ fontWeight: 600, marginBottom: '0.5rem' }}>
            From your Run Plan preview
          </p>
          <ul className="forge-support" style={{ margin: 0, paddingLeft: '1.25rem' }}>
            <li>
              Create: <strong>{preview.artifactsCreate.length}</strong> artifact row(s)
            </li>
            <li>
              Update (set to draft): <strong>{preview.artifactsUpdate.length}</strong> row(s)
            </li>
            <li>
              Untouched (preserve): <strong>{preview.artifactsUntouched.length}</strong> row(s)
            </li>
          </ul>
          <p className="forge-support" style={{ marginTop: '0.65rem', fontSize: '0.9rem', opacity: 0.9 }}>
            Confidence: {preview.confidence.summary}
          </p>
        </div>
      ) : (
        <p className="forge-support" style={{ marginTop: '0.75rem', opacity: 0.85 }}>
          Preview data unavailable — save on a live session to see counts.
        </p>
      )}

      <div style={{ marginTop: '1rem' }}>
        <p className="forge-support" style={{ fontWeight: 600, marginBottom: '0.35rem' }}>
          Generated artifacts (planning, engineering, execution)
        </p>
        {!reviewGenAvailable && (
          <p className="forge-support" style={{ opacity: 0.9, fontSize: '0.9rem' }}>
            Connect to the Lenses server (live session) to generate and review artifacts; local-only mode cannot call
            the API.
          </p>
        )}
        {reviewGenAvailable && onGenerateArtifacts && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem', marginBottom: '0.5rem' }}>
            <button
              type="button"
              className="forge-support"
              disabled={disabled || artifactGenBusy}
              onClick={() => onGenerateArtifacts(null, 'planning')}
            >
              Generate planning pack
            </button>
            <button
              type="button"
              className="forge-support"
              disabled={disabled || artifactGenBusy}
              onClick={() => onGenerateArtifacts(null, 'engineering')}
            >
              Generate engineering pack
            </button>
            <button
              type="button"
              className="forge-support"
              disabled={disabled || artifactGenBusy}
              onClick={() => onGenerateArtifacts(null, 'all')}
            >
              Planning + engineering (all)
            </button>
            <button
              type="button"
              className="forge-support"
              disabled={disabled || artifactGenBusy}
              onClick={() => onGenerateArtifacts(null, 'execution')}
            >
              Generate execution pack
            </button>
            <button
              type="button"
              className="forge-support"
              disabled={disabled || artifactGenBusy}
              onClick={() => onGenerateArtifacts(null, 'complete')}
            >
              Complete stack
            </button>
          </div>
        )}
        {reviewGenAvailable && (onApproveArtifactBundle || onExportArtifacts || onGenerateArtifacts) && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem', marginBottom: '0.5rem' }}>
            <span className="forge-support" style={{ fontSize: '0.88rem', opacity: 0.9, width: '100%' }}>
              Multi-select (checkboxes on cards): regenerate, approve, or export selected slices.
            </span>
            <button
              type="button"
              className="forge-support"
              disabled={disabled || artifactGenBusy || selectedKeys.size === 0}
              onClick={() => onGenerateArtifacts?.(null, undefined, selectedList())}
            >
              Regenerate selected
            </button>
            <button
              type="button"
              className="forge-support"
              disabled={disabled || artifactGenBusy || selectedKeys.size === 0 || !onApproveArtifactBundle}
              onClick={() => onApproveArtifactBundle?.(selectedList())}
            >
              Approve selected
            </button>
            <button
              type="button"
              className="forge-support"
              disabled={disabled || artifactGenBusy || selectedKeys.size === 0 || !onExportArtifacts}
              onClick={() => onExportArtifacts?.(selectedList())}
            >
              Export selected as Markdown
            </button>
          </div>
        )}
        {reviewGenAvailable && onArtifactRecheck && (
          <div style={{ marginBottom: '0.75rem' }}>
            <button
              type="button"
              className="forge-support"
              disabled={disabled || recheckBusy || artifactGenBusy}
              onClick={() => onArtifactRecheck()}
            >
              Run recheck
            </button>
            {recheckSummary && (
              <p className="forge-support" style={{ marginTop: '0.35rem', fontSize: '0.88rem' }}>
                Recheck: {recheckSummary.passed ? 'passed' : 'issues'}{' '}
                {recheckSummary.issues?.length ? `(${recheckSummary.issues.length})` : ''}
              </p>
            )}
            {recheckSummary && recheckSummary.issues && recheckSummary.issues.length > 0 && (
              <ul
                className="forge-support"
                style={{ margin: '0.35rem 0 0', paddingLeft: '1.1rem', fontSize: '0.82rem', maxHeight: '8rem', overflow: 'auto' }}
              >
                {recheckSummary.issues.slice(0, 32).map((issue) => (
                  <li key={issue}>{issue}</li>
                ))}
              </ul>
            )}
          </div>
        )}
        {artifactGenError && (
          <p className="forge-support" role="alert" style={{ color: 'var(--le-danger, #f87171)' }}>
            {artifactGenError}
          </p>
        )}
        <p className="forge-support" style={{ fontWeight: 600, marginBottom: '0.25rem', marginTop: '0.5rem' }}>
          Planning
        </p>
        {PLANNING_ARTIFACT_SLICE_KEYS.map((key) => (
          <ArtifactCard
            key={key}
            sliceKey={key}
            record={arts[key]}
            disabled={disabled || !reviewGenAvailable}
            busy={artifactGenBusy}
            selectable={reviewGenAvailable}
            selected={selectedKeys.has(key)}
            onToggleSelect={() => toggleKey(key)}
            onGenerate={() => onGenerateArtifacts?.(key)}
            onReview={(action, fb) => onArtifactReview?.(action, key, fb)}
          />
        ))}
        <p className="forge-support" style={{ fontWeight: 600, marginBottom: '0.25rem', marginTop: '0.75rem' }}>
          Engineering
        </p>
        {ENGINEERING_ARTIFACT_SLICE_KEYS.map((key) => (
          <ArtifactCard
            key={key}
            sliceKey={key}
            record={arts[key]}
            disabled={disabled || !reviewGenAvailable}
            busy={artifactGenBusy}
            selectable={reviewGenAvailable}
            selected={selectedKeys.has(key)}
            onToggleSelect={() => toggleKey(key)}
            onGenerate={() => onGenerateArtifacts?.(key)}
            onReview={(action, fb) => onArtifactReview?.(action, key, fb)}
          />
        ))}
        <p className="forge-support" style={{ fontWeight: 600, marginBottom: '0.25rem', marginTop: '0.75rem' }}>
          Execution
        </p>
        {EXECUTION_ARTIFACT_SLICE_KEYS.map((key) => (
          <ArtifactCard
            key={key}
            sliceKey={key}
            record={arts[key]}
            disabled={disabled || !reviewGenAvailable}
            busy={artifactGenBusy}
            selectable={reviewGenAvailable}
            selected={selectedKeys.has(key)}
            onToggleSelect={() => toggleKey(key)}
            onGenerate={() => onGenerateArtifacts?.(key)}
            onReview={(action, fb) => onArtifactReview?.(action, key, fb)}
          />
        ))}
      </div>

      <label className="forge-support" htmlFor="bpw-review-note" style={{ display: 'block', marginTop: '0.75rem' }}>
        Notes for this step (saved with the session)
      </label>
      <textarea
        id="bpw-review-note"
        className="le-input"
        style={{ width: '100%', minHeight: '6rem', marginTop: '0.35rem' }}
        value={draftNote}
        disabled={disabled}
        onChange={(e) => onDraftChange(e.target.value)}
        placeholder="Optional notes for review / generate…"
      />
    </div>
  )
}
