import { Link, useSearchParams } from 'react-router-dom'

export type WorkshopPhase = 'discover' | 'score' | 'prioritize' | 'capture'

const PHASES: { id: WorkshopPhase; label: string; hint: string }[] = [
  { id: 'discover', label: 'Discover', hint: 'Capture and arrange ideas on the board.' },
  { id: 'score', label: 'Score', hint: 'Set qualitative impact and effort on each card.' },
  { id: 'prioritize', label: 'Prioritize', hint: 'Sort by impact ÷ effort and agree focus.' },
  { id: 'capture', label: 'Capture', hint: 'Record outcomes in workspace notes or Plan.' },
]

export function BoardWorkshopPhaseStrip({
  phase,
  onPhaseChange,
}: {
  boardId?: string
  phase: WorkshopPhase
  onPhaseChange: (p: WorkshopPhase) => void
}) {
  const [sp] = useSearchParams()
  const repo = sp.get('repo') || ''

  return (
    <section className="le-board-workshop-phases" aria-label="Workshop phases">
      <div className="le-board-workshop-phases__row">
        {PHASES.map((p) => (
          <button
            key={p.id}
            type="button"
            className={`le-btn${phase === p.id ? ' le-btn--primary' : ''}`}
            onClick={() => onPhaseChange(p.id)}
            title={p.hint}
          >
            {p.label}
          </button>
        ))}
      </div>
      {phase === 'capture' ? (
        <p className="forge-support le-board-workshop-phases__lead">
          Export decisions to{' '}
          <Link to="/workspace-md">workspace notes</Link>
          {repo ? (
            <>
              {' '}
              or continue in{' '}
              <Link to={`/plan?repo=${encodeURIComponent(repo)}&from=boards`}>Plan</Link>.
            </>
          ) : null}
        </p>
      ) : (
        <p className="forge-support le-board-workshop-phases__lead">
          {PHASES.find((x) => x.id === phase)?.hint}
        </p>
      )}
    </section>
  )
}
