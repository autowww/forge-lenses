import { Link } from 'react-router-dom'
import { chatRecoveryHref } from '../../lib/uxPageState'

export type StatePanelAiRecoveryProps = {
  prompt: string
  /** Short link label */
  label?: string
}

/** Optional Chat deep-link so users can ask “why” / “what next” without hunting the nav. */
export function StatePanelAiRecovery({ prompt, label = 'Ask Chat for next steps' }: StatePanelAiRecoveryProps) {
  return (
    <p className="le-state-panel__ai-recovery forge-support">
      <Link to={chatRecoveryHref(prompt)} className="le-cc-link">
        {label}
      </Link>
    </p>
  )
}
