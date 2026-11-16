import { Link } from 'react-router-dom'
import { STUDIO_VOCAB } from '../../nav/studioVisibleCopy'

const startHereSteps = [
  {
    title: 'Scope on Plan → Story',
    lead: 'Pick a backlog item and confirm repo scope before any agent recipe runs.',
    to: '/plan?tab=story',
  },
  {
    title: 'Review read-only catalogs',
    lead: 'Versonas, recipes, and tasklets are discovery-only — no autonomous writes from this page.',
    to: '#agentic-catalogs',
  },
  {
    title: 'Check approvals queue',
    lead: 'Write paths stay gated — confirm human approval before packaging or deploy steps.',
    to: '#agentic-approvals',
  },
] as const

/**
 * Start-here journey for AgenticBridgePage — narrative before empty JSON catalogs.
 */
export function AgenticStartHere() {
  return (
    <section className="le-card le-agentic-start-here" aria-labelledby="le-agentic-start-here-h">
      <h2 id="le-agentic-start-here-h" className="le-cc-section__title">
        Start here
      </h2>
      <p className="forge-support">
        Governed agent work begins with intent on {STUDIO_VOCAB.plan}, not raw registry dumps. Follow these steps, then
        browse catalogs when you need a recipe id.
      </p>
      <ol className="le-agentic-start-here__steps">
        {startHereSteps.map((s) => (
          <li key={s.title} className="le-agentic-start-here__step">
            <strong>{s.title}</strong>
            <span className="forge-support"> — {s.lead} </span>
            <Link to={s.to}>Go →</Link>
          </li>
        ))}
      </ol>
    </section>
  )
}
