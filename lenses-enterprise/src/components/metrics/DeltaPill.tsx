import type { CompareModeId } from '../../context/ShellChromeContext'

type Props = {
  text: string
  /** Accessible description (e.g. vs previous period). */
  label: string
  compareMode: CompareModeId
}

export function DeltaPill({ text, label, compareMode }: Props) {
  if (compareMode !== 'previous_period') return null
  return (
    <span className="le-delta-pill" title={label} aria-label={label}>
      {text}
    </span>
  )
}
