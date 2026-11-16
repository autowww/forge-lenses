import { Link } from 'react-router-dom'
import type { WinRepo } from '../../lib/workspacePortfolio'

type Props = {
  wins: WinRepo[]
}

export function RecentWins({ wins }: Props) {
  return (
    <section className="le-cc-section" aria-labelledby="le-cc-wins">
      <h2 id="le-cc-wins" className="le-cc-section__title">
        Recent wins
      </h2>
      <p className="le-cc-section__lead">
        Repositories that look healthy on scan, have a clean working tree, and show lines added in the
        last 7 days (activity without hygiene flags).
      </p>
      {wins.length === 0 ? (
        <p className="le-cc-section__empty">No matching repositories right now.</p>
      ) : (
        <ul className="le-cc-list le-cc-list--wins">
          {wins.map((w) => (
            <li key={w.name}>
              <strong>
                <Link to={`/projects/${encodeURIComponent(w.name)}`}>{w.name}</Link>
              </strong>
              <span className="le-muted"> · {w.linesAdded7d.toLocaleString()} lines added (7d)</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
