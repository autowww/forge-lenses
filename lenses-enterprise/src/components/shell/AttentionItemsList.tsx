import { Link } from 'react-router-dom'
import type { AttentionItem } from './attentionFromWorkspace'

const CAT_LABEL: Record<string, string> = {
  risk: 'Risk',
  evidence_gap: 'Evidence gap',
  decision: 'Decision',
  win: 'Clear',
  dependency: 'Dependency',
  slip: 'Slip',
  catalog: 'Models',
  fleet: 'Fleet',
}

export function AttentionItemsList({ items }: { items: AttentionItem[] }) {
  return (
    <ul className="le-attention__list">
      {items.map((it) => (
        <li key={it.id} className="le-attention__item">
          <span className={`le-attention__badge le-attention__badge--${it.category}`}>
            {CAT_LABEL[it.category] ?? it.category}
          </span>
          <div className="le-attention__body">
            <div className="le-attention__headline">
              {it.to ? (
                <Link to={it.to}>{it.headline}</Link>
              ) : it.href ? (
                <a href={it.href}>{it.headline}</a>
              ) : (
                it.headline
              )}
            </div>
            <div className="le-attention__meta">
              <span className="le-attention__scope">{it.scopeLabel}</span>
              <span className="le-attention__sep" aria-hidden="true">
                ·
              </span>
              <span>{it.actionHint}</span>
            </div>
          </div>
        </li>
      ))}
    </ul>
  )
}
