import { useTraceabilityDrawer } from '../../context/TraceabilityDrawerContext'

type Props = {
  rootId: string
  label: string
  variant?: 'primary' | 'secondary'
  /** Use ``today-band`` to match ``TodayActionBand`` link styling (no ``le-btn``). */
  visual?: 'default' | 'today-band'
  className?: string
  title?: string
}

/**
 * Opens the shared traceability drawer for a canonical orchestration entity id.
 */
export function TraceabilityLaunchButton({
  rootId,
  label,
  variant = 'secondary',
  visual = 'default',
  className = '',
  title,
}: Props) {
  const { openTrace } = useTraceabilityDrawer()
  let cls: string
  if (visual === 'today-band') {
    cls = `le-today-action-band__btn${className ? ` ${className}` : ''}`
  } else if (variant === 'primary') {
    cls = `le-btn le-btn--primary le-btn--small${className ? ` ${className}` : ''}`
  } else {
    cls = `le-btn le-btn--small${className ? ` ${className}` : ''}`
  }

  return (
    <button
      type="button"
      className={cls.trim()}
      title={title}
      onClick={() => openTrace(rootId, { title: title ?? label })}
    >
      {label}
    </button>
  )
}
