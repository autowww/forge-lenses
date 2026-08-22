import { useMemo, useState } from 'react'
import type { FoundryReview } from '../../lib/foundryTypes'

type Props = {
  review: FoundryReview | null | undefined
}

const SOURCE_HINT: Record<string, string> = {
  'git-worktree': 'Diff from the DF worktree commit (what the agent edited).',
  baseline: 'Diff vs the run-start snapshot (before the patch was applied).',
  live: 'Diff vs your live target repo on disk.',
  'git-live': 'Git diff in the live repo after promote.',
  fixture: 'Diff from the offline fixture (before → after) — shown when live repo already matched the fix.',
  none: 'No byte-level diff found; see the explanation above.',
}

export function FoundryDiffReview({ review }: Props) {
  const files = review?.files ?? []
  const [path, setPath] = useState(files[0]?.path ?? '')

  const active = useMemo(() => files.find((f) => f.path === path) ?? files[0], [files, path])
  const narrative = review?.narrative

  if (!review?.ok && !files.length && !review?.proof_markdown && !narrative?.root_cause) {
    return null
  }

  return (
    <section className="le-card" aria-label="Change review">
      <h2 className="le-card__title">Review changes</h2>

      {narrative?.root_cause ? (
        <div className="le-foundry-narrative" aria-label="Change explanation">
          <h3 className="le-foundry-narrative__head">What happened</h3>
          <p>
            <strong>Root cause:</strong> {narrative.root_cause}
          </p>
          {narrative.change_summary ? (
            <p>
              <strong>What changed:</strong> {narrative.change_summary}
            </p>
          ) : null}
          {narrative.why_it_works ? (
            <p>
              <strong>Why this fixes it:</strong> {narrative.why_it_works}
            </p>
          ) : null}
          {narrative.worker_notes?.length ? (
            <details className="le-foundry-proof">
              <summary className="le-foundry-proof__summary">Worker notes</summary>
              <ul className="le-list">
                {narrative.worker_notes.map((n) => (
                  <li key={n}>{n}</li>
                ))}
              </ul>
            </details>
          ) : null}
        </div>
      ) : null}

      <p className="le-muted">
        {review?.promoted
          ? 'Promoted files in the live target working tree. Commit on a feature branch when satisfied.'
          : 'Inspect each file below before approve & promote — no terminal required.'}
      </p>

      {review?.proof_markdown ? (
        <details className="le-foundry-proof">
          <summary className="le-foundry-proof__summary">Technical proof (machine)</summary>
          <pre className="le-preview le-foundry-diff">{review.proof_markdown}</pre>
        </details>
      ) : null}

      {files.length ? (
        <>
          <div className="le-btn-row le-foundry-file-tabs" role="tablist" aria-label="Changed files">
            {files.map((f) => (
              <button
                key={f.path}
                type="button"
                role="tab"
                aria-selected={f.path === (active?.path ?? '')}
                className={`le-btn le-btn--small${f.path === (active?.path ?? '') ? ' le-btn--primary' : ''}`}
                onClick={() => setPath(f.path)}
              >
                {f.path}
              </button>
            ))}
          </div>
          {active?.source ? (
            <p className="le-muted le-foundry-diff-source">
              {SOURCE_HINT[active.source] ?? `Diff source: ${active.source}`}
            </p>
          ) : null}
          {active ? (
            <pre className="le-preview le-foundry-diff" aria-label={`Diff for ${active.path}`}>
              {active.unified_diff?.trim()
                ? active.unified_diff
                : 'No byte diff on disk — the live repo may already include this fix. Re-seed RED on a feature branch for a fresh before/after.'}
            </pre>
          ) : null}
        </>
      ) : (
        <p className="le-muted">No changed files recorded for this run.</p>
      )}
    </section>
  )
}
