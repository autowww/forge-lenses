import './docs-health-project-page.css'

export type CategoryCount = { key: string; label: string; count: number }

type Props = {
  /** First entry should be { key: '', label: 'All', count: totalMatching } */
  tiles: CategoryCount[]
  selectedKey: string
  onSelect: (categoryKey: string) => void
  swimlaneId?: string
}

export function DocsHealthCategorySwimlane({ tiles, selectedKey, onSelect, swimlaneId }: Props) {
  if (!tiles.length) return null

  return (
    <div className="le-dh-cat-swimlane-wrap" id={swimlaneId}>
      <p className="le-muted forge-support" style={{ margin: '0 0 0.35rem', fontSize: '0.82rem' }}>
        Finding categories — click a lane to filter clusters and browse findings below.
      </p>
      <div className="le-dh-cat-swimlane" role="group" aria-label="Finding categories">
        {tiles.map((t) => {
          const selected = selectedKey === t.key
          return (
            <button
              key={t.key === '' ? '__all__' : t.key}
              type="button"
              aria-pressed={selected}
              className={`le-dh-cat-tile${selected ? ' le-dh-cat-tile--selected' : ''}`}
              onClick={() => onSelect(t.key)}
            >
              <span className="le-dh-cat-tile__label">{t.label}</span>
              <span className="le-dh-cat-tile__count">{t.count}</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
