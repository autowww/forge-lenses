import { useMemo } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { buildSuggestionFindResults } from '../commandBar/buildContextualCommands'
import { useStudioCommandBar } from '../context/StudioCommandBarContext'

/**
 * Compact contextual shortcuts — opens command bar (Ask) or navigates for pre-built flows.
 */
export function StudioInlineAssist() {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const cmd = useStudioCommandBar()

  const chips = useMemo(() => {
    const slug = pathname.match(/^\/projects\/([^/]+)/)?.[1]
      ? decodeURIComponent(pathname.match(/^\/projects\/([^/]+)/)![1])
      : undefined
    return buildSuggestionFindResults(pathname, slug)
      .filter((s) => s.kind === 'suggestion')
      .slice(0, 4)
  }, [pathname])

  if (chips.length === 0) return null

  return (
    <section className="le-inline-assist le-inline-assist--quiet" aria-label="Suggested actions for this page">
      <span className="le-inline-assist__label">Quick assist (Ask / Do)</span>
      <div className="le-inline-assist__chips">
        {chips.map((c) => (
          <button
            key={c.id}
            type="button"
            className="le-inline-assist__chip"
            onClick={() => {
              if (c.askPrefill) {
                cmd.open('ask', { initialQuery: c.askPrefill })
              } else if (c.to?.startsWith('/chat')) {
                const m = c.to.match(/[?&]prefill=([^&]*)/)
                const pre = m?.[1] ? decodeURIComponent(m[1].replace(/\+/g, ' ')) : ''
                cmd.open('ask', { initialQuery: pre })
              } else if (c.to) {
                navigate(c.to)
              }
            }}
          >
            {c.label}
          </button>
        ))}
      </div>
    </section>
  )
}
