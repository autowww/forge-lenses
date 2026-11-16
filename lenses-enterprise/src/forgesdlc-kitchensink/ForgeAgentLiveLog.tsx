import { useEffect, useRef } from 'react'
import './forge-live-ui.css'

export type ForgeAgentLiveLogLine = {
  id: string
  /** ISO timestamp for display. */
  ts?: string
  text: string
  tone?: 'info' | 'ok' | 'err' | 'busy'
}

export type ForgeAgentLiveLogProps = {
  lines: ForgeAgentLiveLogLine[]
  /** Format clock for each line (optional). */
  formatTs?: (iso: string) => string
  className?: string
  emptyHint?: string
  maxHeight?: string
}

/**
 * Cursor-style scrolling activity log (`role="log"`, polite live region).
 */
export function ForgeAgentLiveLog({
  lines,
  formatTs = (iso) => {
    try {
      return new Date(iso).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    } catch {
      return iso
    }
  },
  className = '',
  emptyHint = 'Waiting for the first model or tool events…',
  maxHeight = 'min(36vh, 22rem)',
}: ForgeAgentLiveLogProps) {
  const ref = useRef<HTMLDivElement>(null)
  const prev = useRef(0)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const grew = lines.length > prev.current
    prev.current = lines.length
    if (!grew && lines.length > 0) return
    window.requestAnimationFrame(() => {
      el.scrollTop = el.scrollHeight
    })
  }, [lines])

  return (
    <div
      ref={ref}
      className={`ks-fe-agentlog ${className}`.trim()}
      role="log"
      aria-relevant="additions"
      aria-live="polite"
      style={{ maxHeight }}
    >
      {!lines.length ? (
        <p className="ks-fe-agentlog__empty forge-support">{emptyHint}</p>
      ) : (
        <ul className="ks-fe-agentlog__list">
          {lines.map((ln) => (
            <li key={ln.id} className={`ks-fe-agentlog__line ks-fe-agentlog__line--${ln.tone || 'info'}`}>
              {ln.ts ? <span className="ks-fe-agentlog__ts">{formatTs(ln.ts)}</span> : null}
              <span className="ks-fe-agentlog__text">{ln.text}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
