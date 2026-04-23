import { Link } from 'react-router-dom'
import { parseTodayCharge } from '../../lib/todayCharge'
import { STUDIO_VOCAB } from '../../nav/studioVisibleCopy'
import { SparkTable } from './TodayChargeView'

type Props = {
  payload: Record<string, unknown> | null
}

export function BlockersNeedingAction({ payload }: Props) {
  const { sections } = parseTodayCharge(payload)
  const blocked = sections.blocked ?? []

  return (
    <section className="le-delivery-section" aria-labelledby="le-delivery-block-h">
      <h2 id="le-delivery-block-h" className="le-delivery-section__title">
        Blockers needing action
      </h2>
      <p className="le-delivery-section__lead">Items in the blocked section from today-charge.</p>
      {!payload ? (
        <p className="le-delivery-section__empty">No data.</p>
      ) : blocked.length === 0 ? (
        <p className="le-delivery-section__empty">No blocked rows right now.</p>
      ) : (
        <>
          <SparkTable rows={blocked} />
          <p className="le-delivery-section__actions forge-support">
            <Link className="le-delivery-link" to="/workspace-md">
              {STUDIO_VOCAB.workspaceNotes}
            </Link>
            {' · '}
            <Link className="le-delivery-link" to="/projects?filter=dirty">
              Dirty repos
            </Link>
          </p>
        </>
      )}
    </section>
  )
}
