import type { FoundryCapabilities } from '../../lib/foundryTypes'

type Props = {
  capabilities: FoundryCapabilities | null
}

function tone(status: string | undefined): string {
  switch (status) {
    case 'available':
      return 'success'
    case 'stub':
      return 'warning'
    default:
      return 'neutral'
  }
}

export function FoundryCapabilitiesCard({ capabilities }: Props) {
  const ladder = capabilities?.ladder ?? {}
  const levels = Object.entries(ladder)
  if (!levels.length) return null
  return (
    <section className="le-card" aria-label="Dark Factory autonomy ladder">
      <h2 className="le-card__title">Autonomy ladder</h2>
      <p className="le-muted">
        Studio wires L1 draft runs only. Higher levels return honest stubs until Dark Factory L2/L3 ship.
      </p>
      <ul className="le-list">
        {levels.map(([level, meta]) => (
          <li key={level}>
            <strong>{level}</strong> — {meta.label ?? level}{' '}
            <span className={`le-badge le-badge--${tone(meta.status)}`}>{meta.status ?? 'unknown'}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}
