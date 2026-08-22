type Props = {
  resolvedAt?: string | null
  /** When true, scope is complete enough for higher confidence labels. */
  scopeComplete?: boolean
}

function ageHours(iso: string): number | null {
  const t = Date.parse(iso)
  if (Number.isNaN(t)) return null
  return (Date.now() - t) / (1000 * 60 * 60)
}

/**
 * Interpreted scan freshness / confidence chip for Plan and Today headers.
 */
export function FreshnessChip({ resolvedAt, scopeComplete = false }: Props) {
  const hours = resolvedAt ? ageHours(resolvedAt) : null
  let freshnessLabel = 'Scan unknown'
  let tone: 'ok' | 'warn' | 'muted' = 'muted'

  if (hours != null) {
    if (hours < 2) {
      freshnessLabel = 'Fresh scan'
      tone = 'ok'
    } else if (hours < 24) {
      freshnessLabel = 'Recent scan'
      tone = 'ok'
    } else if (hours < 72) {
      freshnessLabel = 'Aging scan'
      tone = 'warn'
    } else {
      freshnessLabel = 'Stale scan'
      tone = 'warn'
    }
  }

  const confidence = scopeComplete ? 'High confidence' : 'Scope incomplete'

  return (
    <span className={`le-freshness-chip le-freshness-chip--${tone}`} title={resolvedAt ?? undefined}>
      <span className="freshnessChip">{freshnessLabel}</span>
      <span className="le-freshness-chip__sep" aria-hidden>
        ·
      </span>
      <span className="freshnessLabel">{confidence}</span>
    </span>
  )
}
