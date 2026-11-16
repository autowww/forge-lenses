import { useId, useState } from 'react'

type Props = {
  /** Repo-relative path (shown when expanded). */
  filePath: string
  /**
   * When true, chip + reveal sit in a vertical stack (e.g. plan tiles).
   * When false, fragment children pair with a CSS grid parent (`le-plan-scope__picker-block--grid`).
   */
  stacked?: boolean
}

/**
 * Small “MD” control: full path stays hidden until the user asks (expand inline or hover title).
 * Clicks do not propagate — safe beside a row select action.
 */
export function PlanScopeFilePathChip({ filePath, stacked = false }: Props) {
  const [open, setOpen] = useState(false)
  const revealId = useId()

  if (!filePath.trim()) return null

  const chip = (
    <button
      type="button"
      className="le-plan-scope__path-md-chip"
      aria-expanded={open}
      aria-controls={open ? revealId : undefined}
      title={filePath}
      onClick={(e) => {
        e.preventDefault()
        e.stopPropagation()
        setOpen((v) => !v)
      }}
    >
      MD
    </button>
  )

  const reveal = open ? (
    <div id={revealId} className="le-plan-scope__path-md-reveal le-mono" role="region">
      {filePath}
    </div>
  ) : null

  if (stacked) {
    return (
      <div className="le-plan-scope__path-chip-stack">
        {chip}
        {reveal}
      </div>
    )
  }

  return (
    <>
      {chip}
      {reveal}
    </>
  )
}
