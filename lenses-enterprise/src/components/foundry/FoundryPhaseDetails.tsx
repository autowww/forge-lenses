import type { FoundryPhase } from '../../lib/foundryTypes'

type Props = {
  phases: FoundryPhase[]
  selectedId?: string | null
  onSelect?: (phaseId: string) => void
}

function statusLabel(status: string): string {
  return status.replace(/_/g, ' ')
}

export function FoundryPhaseDetails({ phases, selectedId, onSelect }: Props) {
  const active = phases.filter((p) => p.status !== 'not_started' || p.detail)
  if (!active.length) return null

  return (
    <section className="le-card" aria-label="Workflow stage details">
      <h2 className="le-card__title">Stage details</h2>
      <p className="le-muted">Tap a stage in the bar above to highlight it. Each row shows what Dark Factory recorded.</p>
      <ul className="le-list le-foundry-phases">
        {active.map((p) => {
          const isSel = selectedId === p.id
          return (
            <li key={p.id}>
              <button
                type="button"
                className={`le-foundry-phases__row${isSel ? ' le-foundry-phases__row--selected' : ''}`}
                onClick={() => onSelect?.(p.id)}
                aria-pressed={isSel}
              >
                <span className="le-foundry-phases__label">{p.label}</span>
                <span className={`le-foundry-phases__status le-foundry-phases__status--${p.status}`}>
                  {statusLabel(p.status)}
                </span>
                {p.detail ? <span className="le-foundry-phases__detail">{p.detail}</span> : null}
              </button>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
