import { Link } from 'react-router-dom'
import { STUDIO_VOCAB } from '../../nav/studioVisibleCopy'

type Props = {
  hasChargeArtifact: boolean
}

export function DecisionBacklog({ hasChargeArtifact }: Props) {
  return (
    <section className="le-cc-section" aria-labelledby="le-cc-decisions">
      <h2 id="le-cc-decisions" className="le-cc-section__title">
        Decision backlog
      </h2>
      <p className="le-cc-section__lead">
        Leadership decisions are best captured in forge artifacts — not inferred from git alone.
      </p>
      {hasChargeArtifact ? (
        <p className="le-cc-decision-copy">
          <strong>Charge artifacts detected.</strong> Open {STUDIO_VOCAB.workspaceNotes.toLowerCase()} to review
          recorded decisions and follow-ups.
        </p>
      ) : (
        <p className="le-cc-decision-copy">
          No <code className="le-mono">forge/charge.md</code> detected under scanned repos. Add charge
          where you want decisions and rationale to stay traceable.
        </p>
      )}
      <p className="le-cc-decision-actions">
        <Link className="le-cc-link" to="/workspace-md">
          {STUDIO_VOCAB.workspaceNotes}
        </Link>
        {' · '}
        <Link className="le-cc-link" to="/plan">
          {STUDIO_VOCAB.plan}
        </Link>
      </p>
    </section>
  )
}
