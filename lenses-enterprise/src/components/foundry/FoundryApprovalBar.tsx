import { useState } from 'react'

type Props = {
  runId: string
  disabled?: boolean
  onApprove: (confirm: boolean) => Promise<void>
}

export function FoundryApprovalBar({ runId, disabled, onApprove }: Props) {
  const [checked, setChecked] = useState(false)
  const [busy, setBusy] = useState(false)

  const onClick = async () => {
    if (!checked) return
    setBusy(true)
    try {
      await onApprove(true)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="le-card" aria-label="Human approval before promote">
      <h2 className="le-card__title">Review before apply</h2>
      <p className="le-muted">
        Draft run <code>{runId}</code> passed assay. Promote copies changed files into the live target working tree
        (file scope). Commit on a feature branch per branching policy — Studio does not auto-commit.
      </p>
      <label className="le-check-row">
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => setChecked(e.target.checked)}
          disabled={disabled || busy}
        />
        I reviewed the diff and approve promoting changed files
      </label>
      <div className="le-btn-row" style={{ marginTop: '0.75rem' }}>
        <button
          type="button"
          className="le-btn le-btn--primary"
          disabled={!checked || disabled || busy}
          onClick={() => void onClick()}
        >
          Approve and promote
        </button>
      </div>
    </section>
  )
}
