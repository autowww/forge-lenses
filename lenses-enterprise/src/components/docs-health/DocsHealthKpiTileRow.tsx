import type { DocsHealthScore } from '../../api/docsHealth'
import './docs-health-project-page.css'

type Props = {
  score: DocsHealthScore | undefined
  selectedScoreArea: string | null
  onToggleScoreArea: (key: string) => void
}

export function DocsHealthKpiTileRow({ score, selectedScoreArea, onToggleScoreArea }: Props) {
  const entries = score?.sub_scores ? Object.entries(score.sub_scores) : []
  if (!entries.length) return null

  return (
    <div className="le-dh-kpi-row" role="group" aria-label="Score by category — click to filter clusters">
      {entries.map(([k, v]) => {
        const selected = selectedScoreArea === k
        return (
          <button
            key={k}
            type="button"
            className={`le-dh-kpi-tile${selected ? ' le-dh-kpi-tile--selected' : ''}`}
            aria-pressed={selected}
            onClick={() => onToggleScoreArea(k)}
          >
            <div className="le-dh-kpi-tile__label">{k.replace(/_/g, ' ')}</div>
            <div className="le-dh-kpi-tile__value">{v.value ?? '—'}</div>
            <div className="le-dh-kpi-tile__weight">weight {(v.weight ?? 0).toFixed(2)}</div>
          </button>
        )
      })}
    </div>
  )
}
