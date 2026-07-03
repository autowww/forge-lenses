import type { FoundryRun } from '../../lib/foundryTypes'

type Props = {
  run: FoundryRun
}

export function FoundryAssayCard({ run }: Props) {
  const passed = run.assay_ok === true && run.final_status === 'pass'
  const assay = run.assay ?? {}
  return (
    <section className="le-card" aria-label="Assay verdict">
      <h2 className="le-card__title">{passed ? 'Assay passed' : 'Assay verdict'}</h2>
      <p className="le-muted">
        Final status: <strong>{run.final_status ?? run.status ?? 'unknown'}</strong>
        {run.promoted ? ' · Promoted to target working tree' : ''}
      </p>
      <ul className="le-list">
        {typeof assay.tests_pass === 'boolean' ? (
          <li>tests_pass: {assay.tests_pass ? 'yes' : 'no'}</li>
        ) : null}
        {typeof assay.acceptance_criteria_met === 'boolean' ? (
          <li>acceptance_criteria_met: {assay.acceptance_criteria_met ? 'yes' : 'no'}</li>
        ) : null}
        {typeof assay.risks_reviewed === 'boolean' ? (
          <li>risks_reviewed: {assay.risks_reviewed ? 'yes' : 'no'}</li>
        ) : null}
      </ul>
      {run.proof?.files_changed ? (
        <p className="le-muted">
          Changed: {Array.isArray(run.proof.files_changed) ? run.proof.files_changed.join(', ') : '—'}
        </p>
      ) : null}
    </section>
  )
}
