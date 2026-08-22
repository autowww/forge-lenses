import { useEffect, useState } from 'react'

type Props = {
  startedAt: number
  /** Visible prefix (also used for a11y). */
  statusLabel?: string
  className?: string
}

/**
 * Animated “thinking” dots plus elapsed whole seconds while a chat request is in flight.
 */
export function ChatRequestPendingRow({
  startedAt,
  statusLabel = 'Waiting for response',
  className,
}: Props) {
  const [sec, setSec] = useState(0)
  useEffect(() => {
    const tick = () => setSec(Math.max(0, Math.floor((Date.now() - startedAt) / 1000)))
    tick()
    const id = window.setInterval(tick, 250)
    return () => window.clearInterval(id)
  }, [startedAt])

  const rootClass = ['le-chat-pending', className].filter(Boolean).join(' ')

  return (
    <div className={rootClass} role="status" aria-live="polite" aria-atomic="true">
      <span className="le-chat-pending__label">{statusLabel}</span>
      <span className="le-chat-pending__dots" aria-hidden>
        <span className="le-chat-pending__dot" />
        <span className="le-chat-pending__dot" />
        <span className="le-chat-pending__dot" />
      </span>
      <span className="le-chat-pending__elapsed">{sec}s</span>
    </div>
  )
}
