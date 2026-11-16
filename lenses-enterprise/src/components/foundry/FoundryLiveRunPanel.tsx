import { useMemo } from 'react'
import {
  ForgeAgentLiveLog,
  ForgeLivePulse,
  ForgeRunProgressTrack,
} from '../../forgesdlc-kitchensink'
import { useElapsedSecondsSince } from '../../hooks/useElapsedSecondsSince'
import type { FoundryRun } from '../../lib/foundryTypes'
import { foundryActivityToLogLines, foundryProgressFromPhases } from '../../lib/foundryActivity'

type Props = {
  run: FoundryRun
}

export function FoundryLiveRunPanel({ run }: Props) {
  const isLive = run.status === 'running' || run.status === 'pending'
  const elapsed = useElapsedSecondsSince(run.created_at)
  const logLines = useMemo(() => foundryActivityToLogLines(run.activity), [run.activity])
  const { percent, milestones } = useMemo(() => foundryProgressFromPhases(run.phases), [run.phases])

  const stepLabel = run.current_phase
    ? run.current_phase.replace(/-/g, ' ')
    : isLive
      ? 'Dark Factory driver'
      : ''

  return (
    <section className="le-card le-foundry-live" aria-label="Agent run activity">
      <h2 className="le-card__title">Agent activity</h2>
      <p className="le-muted le-foundry-live__lead">
        <ForgeLivePulse active={isLive} label={isLive ? 'Live · polling' : 'Finished'} />{' '}
        {isLive && stepLabel ? (
          <>
            <strong>Step in flight:</strong> {stepLabel}
            {elapsed > 0 ? ` · ${elapsed}s elapsed` : null}
          </>
        ) : isLive ? (
          'Waiting for the first Dark Factory phase…'
        ) : (
          'Run log — chronological agent and driver events.'
        )}
      </p>
      <ForgeRunProgressTrack
        percent={isLive ? percent : run.status === 'completed' ? 100 : percent}
        milestones={milestones}
        aria-label="Foundry run progress"
      />
      <ForgeAgentLiveLog
        lines={logLines}
        maxHeight="min(42vh, 26rem)"
        emptyHint="Activity will stream here as Dark Factory classifies, plans, drafts, and verifies."
      />
    </section>
  )
}
