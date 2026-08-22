import { Link } from 'react-router-dom'
import { chatRecoveryHref } from '../../lib/uxPageState'

export type AssistShortcutAction = { prompt: string; label: string }

export type StatePanelAssistShortcutsProps = {
  actions: AssistShortcutAction[]
}

/** Compact list of Copilot deep-links for contextual recovery (Sprint UX0). */
export function StatePanelAssistShortcuts({ actions }: StatePanelAssistShortcutsProps) {
  if (!actions.length) return null
  return (
    <div className="le-state-panel__assist-shortcuts" role="group" aria-label="Guided help in Copilot">
      <p className="le-state-panel__assist-shortcuts-lead forge-support">Guided help</p>
      <ul className="le-state-panel__assist-shortcuts-list">
        {actions.map((a) => (
          <li key={a.label}>
            <Link to={chatRecoveryHref(a.prompt)} className="le-cc-link">
              {a.label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  )
}
