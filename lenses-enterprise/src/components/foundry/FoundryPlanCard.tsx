import type { FoundryPlan } from '../../lib/foundryTypes'

type Props = {
  plan: FoundryPlan | null
  busy?: boolean
  onRunDraft?: () => void
}

export function FoundryPlanCard({ plan, busy, onRunDraft }: Props) {
  if (!plan) return null
  if (!plan.ok) {
    return (
      <section className="le-card" aria-label="Plan proposal">
        <h2 className="le-card__title">Plan unavailable</h2>
        <p className="le-muted">{plan.error ?? plan.reason ?? 'Could not build a plan for this request.'}</p>
      </section>
    )
  }
  const units = plan.units ?? []
  return (
    <section className="le-card" aria-label="Plan proposal">
      <h2 className="le-card__title">Proposed plan</h2>
      <p className="le-muted">
        Goal: <strong>{plan.goal}</strong> · Level: <strong>{plan.level}</strong>
      </p>
      <ul className="le-list">
        {units.map((u) => (
          <li key={u.id ?? u.summary}>
            {u.summary ?? u.id}
            {u.allowed_files?.length ? (
              <span className="le-muted"> — files: {u.allowed_files.join(', ')}</span>
            ) : null}
          </li>
        ))}
      </ul>
      {onRunDraft ? (
        <div className="le-btn-row" style={{ marginTop: '0.75rem' }}>
          <button type="button" className="le-btn le-btn--primary" disabled={busy} onClick={onRunDraft}>
            Run L1 draft
          </button>
        </div>
      ) : null}
    </section>
  )
}
