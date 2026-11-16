/**
 * Read-only deterministic preview for Run Plan step (step 8).
 */

import type { CSSProperties, ReactNode } from 'react'
import type { RunPlanPreview } from './runPlanPreviewTypes'
import { WIZARD_STEPS } from './wizardSteps'

const cardStyle: CSSProperties = {
  marginTop: '0.75rem',
  padding: '0.75rem',
  border: '1px solid rgba(255,255,255,0.12)',
  borderRadius: '6px',
}

type Props = {
  preview: RunPlanPreview
  /** Jump to a prior wizard step to edit inputs (optional). */
  onJumpToStep?: (stepIndex: number) => void
  disabled?: boolean
}

function Section({
  id,
  title,
  children,
}: {
  id: string
  title: string
  children: ReactNode
}) {
  return (
    <section className="forge-support" aria-labelledby={id} style={cardStyle}>
      <h3 id={id} className="forge-support" style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '0.5rem' }}>
        {title}
      </h3>
      {children}
    </section>
  )
}

function BulletList({ items }: { items: string[] }) {
  if (items.length === 0) {
    return <p className="forge-support" style={{ opacity: 0.85 }}>(none)</p>
  }
  return (
    <ul className="forge-support" style={{ margin: '0.25rem 0 0 1rem', padding: 0 }}>
      {items.map((x, i) => (
        <li key={`${i}-${x.slice(0, 64)}`} style={{ marginBottom: '0.35rem' }}>
          {x}
        </li>
      ))}
    </ul>
  )
}

function ArtifactTable({ rows }: { rows: { label: string; reason?: string }[] }) {
  if (rows.length === 0) {
    return <p className="forge-support" style={{ opacity: 0.85 }}>(none)</p>
  }
  return (
    <table className="forge-support" style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
      <thead>
        <tr>
          <th style={{ textAlign: 'left', padding: '0.25rem', borderBottom: '1px solid rgba(255,255,255,0.12)' }}>
            Artifact
          </th>
          <th style={{ textAlign: 'left', padding: '0.25rem', borderBottom: '1px solid rgba(255,255,255,0.12)' }}>
            Note
          </th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.label}>
            <td style={{ padding: '0.35rem 0.25rem', verticalAlign: 'top' }}>{r.label}</td>
            <td style={{ padding: '0.35rem 0.25rem', verticalAlign: 'top', opacity: 0.9 }}>{r.reason ?? '—'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export function RunPlanPreviewPanel({ preview, onJumpToStep, disabled }: Props) {
  const jump = (i: number) => {
    if (disabled || !onJumpToStep) return
    onJumpToStep(i)
  }

  return (
    <div className="forge-support" style={{ marginBottom: '1rem' }}>
      <p className="forge-support" style={{ fontWeight: 600, marginBottom: '0.5rem' }}>
        What will run (preview)
      </p>
      <p className="forge-support" style={{ marginBottom: '0.75rem', opacity: 0.9, fontSize: '0.92rem' }}>
        Deterministic plan from your mission, intake, foundation brief, clarifications, target pack, autonomy, and scope.
        No artifacts are generated on this step — review and adjust earlier steps if needed.
      </p>

      {onJumpToStep && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem', marginBottom: '0.5rem' }}>
          {WIZARD_STEPS.map((label, i) =>
            i < 8 ? (
              <button
                key={label}
                type="button"
                className="forge-support"
                disabled={disabled}
                onClick={() => jump(i)}
                title={`Go to ${label}`}
              >
                Edit: {label}
              </button>
            ) : null,
          )}
        </div>
      )}

      <Section id="bpw-preview-confidence" title="Confidence">
        <p className="forge-support" style={{ margin: 0 }}>
          {preview.confidence.summary} (score {preview.confidence.score01.toFixed(2)})
        </p>
      </Section>

      <Section id="bpw-preview-current" title={preview.currentState.title}>
        <BulletList items={preview.currentState.bullets} />
      </Section>

      <Section id="bpw-preview-target" title={preview.targetState.title}>
        <BulletList items={preview.targetState.bullets} />
      </Section>

      <Section id="bpw-preview-artifacts-create" title="Artifacts to create">
        <ArtifactTable rows={preview.artifactsCreate} />
      </Section>

      <Section id="bpw-preview-artifacts-update" title="Artifacts to update">
        <ArtifactTable rows={preview.artifactsUpdate} />
      </Section>

      <Section id="bpw-preview-artifacts-untouched" title="Artifacts to leave untouched">
        <ArtifactTable rows={preview.artifactsUntouched} />
      </Section>

      <Section id="bpw-preview-gates" title="Review gates">
        <ul className="forge-support" style={{ margin: '0.25rem 0 0 1rem', padding: 0 }}>
          {preview.reviewGates.map((g) => (
            <li key={g.id} style={{ marginBottom: '0.5rem' }}>
              <strong>{g.title}</strong>
              <div style={{ opacity: 0.9, fontSize: '0.9rem' }}>{g.rationale}</div>
            </li>
          ))}
        </ul>
      </Section>

      <Section id="bpw-preview-assumptions" title="Assumptions relied on">
        <BulletList items={preview.assumptionsReliedOn} />
      </Section>

      <Section id="bpw-preview-blockers" title="Blockers / missing dependencies">
        {preview.blockers.length === 0 ? (
          <p className="forge-support" style={{ opacity: 0.85 }}>No hard blockers detected from structured checks.</p>
        ) : (
          <BulletList items={preview.blockers} />
        )}
      </Section>

      <Section id="bpw-preview-risks" title="Risk hotspots">
        {preview.riskHotspots.length === 0 ? (
          <p className="forge-support" style={{ opacity: 0.85 }}>(none flagged)</p>
        ) : (
          <ul className="forge-support" style={{ margin: '0.25rem 0 0 1rem', padding: 0 }}>
            {preview.riskHotspots.map((r) => (
              <li key={r.id} style={{ marginBottom: '0.45rem' }}>
                <span style={{ textTransform: 'uppercase', fontSize: '0.75rem', opacity: 0.85 }}>{r.severity}</span>{' '}
                — {r.label}: {r.detail}
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section id="bpw-preview-scope" title="Scope boundaries">
        <BulletList items={preview.scopeBoundaries} />
      </Section>
    </div>
  )
}
