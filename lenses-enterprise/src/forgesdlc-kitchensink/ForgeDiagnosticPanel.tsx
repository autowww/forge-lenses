import { useId, useState, type ReactNode } from 'react'

export type ForgeDiagnosticPanelProps = {
  title?: string
  summary: ReactNode
  raw: unknown
  className?: string
  defaultRawOpen?: boolean
}

function safeStringify(v: unknown): string {
  try {
    return JSON.stringify(v, null, 2)
  } catch {
    return String(v)
  }
}

/**
 * Diagnostics: human-readable summary first; raw JSON only behind disclosure.
 */
export function ForgeDiagnosticPanel({
  title = 'Diagnostics',
  summary,
  raw,
  className = '',
  defaultRawOpen = false,
}: ForgeDiagnosticPanelProps) {
  const id = useId()
  const [open, setOpen] = useState(defaultRawOpen)
  const preId = `${id}-raw`

  return (
    <section className={`ks-fe-diag ${className}`.trim()} aria-labelledby={`${id}-h`}>
      <h3 id={`${id}-h`} className="ks-fe-diag__title">
        {title}
      </h3>
      <div className="ks-fe-diag__summary">{summary}</div>
      <div className="ks-fe-diag__raw">
        <button
          type="button"
          className="ks-fe-diag__raw-toggle le-btn le-btn--small le-btn--ghost"
          aria-expanded={open}
          aria-controls={preId}
          onClick={() => setOpen((v) => !v)}
        >
          {open ? 'Hide raw JSON' : 'Show raw JSON'}
        </button>
        {open ? (
          <pre id={preId} className="le-preview le-json ks-fe-diag__pre">
            {safeStringify(raw)}
          </pre>
        ) : null}
      </div>
    </section>
  )
}
