import './docs-health-project-page.css'

export type DocsHealthProjectView = 'dashboard' | 'queue' | 'running' | 'completed' | 'failed'

const ITEMS: { id: DocsHealthProjectView; label: string }[] = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'queue', label: 'Run queue' },
  { id: 'running', label: 'Running now' },
  { id: 'completed', label: 'Completed' },
  { id: 'failed', label: 'Failed' },
]

type Props = {
  active: DocsHealthProjectView
  onChange: (v: DocsHealthProjectView) => void
  navId?: string
}

export function DocsHealthProjectSubNav({ active, onChange, navId }: Props) {
  return (
    <nav className="le-dh-proj-nav" aria-label="Docs health views" id={navId}>
      {ITEMS.map(({ id, label }) => (
        <button
          key={id}
          type="button"
          className="le-dh-proj-nav__btn"
          aria-current={active === id ? 'true' : undefined}
          onClick={() => onChange(id)}
        >
          {label}
        </button>
      ))}
    </nav>
  )
}
