import { useEffect, useId, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiGetJson } from '../../api/http'
import type { UsageSummary } from '../LlmSettingsForm'
import { STUDIO_VOCAB } from '../../nav/studioVisibleCopy'

function sumUsage(u: UsageSummary | null): {
  totalTokens: number
  promptTokens: number
  completionTokens: number
  attempts: number
  failures: number
} {
  const out = { totalTokens: 0, promptTokens: 0, completionTokens: 0, attempts: 0, failures: 0 }
  if (!u?.totals) return out
  for (const t of Object.values(u.totals)) {
    if (!t || typeof t !== 'object') continue
    out.totalTokens += Number(t.total_tokens || 0)
    out.promptTokens += Number(t.prompt_tokens || 0)
    out.completionTokens += Number(t.completion_tokens || 0)
    out.attempts += Number(t.attempts ?? t.requests ?? 0)
    out.failures += Number(t.failures || 0)
  }
  return out
}

/** Home overview: workspace LLM token totals and link to AI Setup detail. */
export function HomeLlmUsageBand() {
  const hId = useId()
  const [usage, setUsage] = useState<UsageSummary | null>(null)
  const [loadFailed, setLoadFailed] = useState(false)

  useEffect(() => {
    let cancelled = false
    void apiGetJson<{ ok?: boolean; usage?: UsageSummary }>('/api/llm/usage')
      .then((r) => {
        if (cancelled) return
        if (r?.usage) setUsage(r.usage)
        else setUsage(null)
      })
      .catch(() => {
        if (!cancelled) {
          setUsage(null)
          setLoadFailed(true)
        }
      })
    return () => {
      cancelled = true
    }
  }, [])

  const sums = useMemo(() => sumUsage(usage), [usage])

  const lastOk = usage?.last_ok || {}
  const lastLines = useMemo(() => {
    const rows = Object.entries(lastOk)
      .map(([pid, iso]) => ({ pid, iso: String(iso || '').trim() }))
      .filter((x) => x.iso)
      .slice(0, 6)
    return rows
  }, [lastOk])

  const perProvider = useMemo(() => {
    if (!usage?.totals) return []
    return Object.entries(usage.totals)
      .map(([pid, t]) => ({
        pid,
        tt: Number(t?.total_tokens || 0),
        att: Number(t?.attempts ?? t?.requests ?? 0),
        fail: Number(t?.failures || 0),
      }))
      .filter((x) => x.tt > 0 || x.att > 0 || x.fail > 0)
      .sort((a, b) => b.tt - a.tt)
  }, [usage])

  return (
    <section className="le-panel" aria-labelledby={hId}>
      <h2 id={hId} className="le-panel__title">
        LLM usage (workspace)
      </h2>
      {loadFailed ? (
        <p className="forge-support">Could not load usage from the Lenses API.</p>
      ) : (
        <p className="forge-support">
          Token counts come from providers that return usage on completions (Ollama, OpenAI-compatible, OpenAI,
          Anthropic, Gemini). This is the same data as <strong>{STUDIO_VOCAB.llmPreferences}</strong> → Provider health
          and usage.
        </p>
      )}
      <div
        className="le-muted"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(10rem, 1fr))',
          gap: '0.5rem',
          marginTop: '0.5rem',
        }}
      >
        <div className="le-panel" style={{ padding: '0.5rem 0.65rem' }}>
          <div className="le-muted" style={{ fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Total tokens (all providers)
          </div>
          <div style={{ fontWeight: 700, fontSize: '1.15rem' }}>{sums.totalTokens.toLocaleString()}</div>
        </div>
        <div className="le-panel" style={{ padding: '0.5rem 0.65rem' }}>
          <div className="le-muted" style={{ fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            In + out (sum)
          </div>
          <div style={{ fontWeight: 700 }}>
            {sums.promptTokens.toLocaleString()} + {sums.completionTokens.toLocaleString()}
          </div>
        </div>
        <div className="le-panel" style={{ padding: '0.5rem 0.65rem' }}>
          <div className="le-muted" style={{ fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Attempts / failures
          </div>
          <div style={{ fontWeight: 700 }}>
            {sums.attempts.toLocaleString()} / {sums.failures.toLocaleString()}
          </div>
        </div>
      </div>
      {perProvider.length > 0 ? (
        <ul className="forge-support" style={{ marginTop: '0.65rem', paddingLeft: '1.1rem' }}>
          {perProvider.map((r) => (
            <li key={r.pid}>
              <strong>{r.pid}</strong>: {r.tt.toLocaleString()} tokens · {r.att} attempt(s)
              {r.fail ? ` · ${r.fail} failure(s)` : ''}
            </li>
          ))}
        </ul>
      ) : !loadFailed ? (
        <p className="forge-support" style={{ marginTop: '0.55rem' }}>
          No token totals yet — run <strong>Ask</strong> from the header, Copilot, or Try Chat in {STUDIO_VOCAB.llmPreferences}.
        </p>
      ) : null}
      {lastLines.length > 0 ? (
        <p className="forge-support" style={{ marginTop: '0.45rem' }}>
          Last successful call:{' '}
          {lastLines.map((x, i) => (
            <span key={x.pid}>
              {i > 0 ? ' · ' : null}
              <strong>{x.pid}</strong> <time dateTime={x.iso}>{x.iso}</time>
            </span>
          ))}
        </p>
      ) : null}
      <p className="forge-support" style={{ marginTop: '0.5rem' }}>
        <Link to="/settings/llm">Open {STUDIO_VOCAB.llmPreferences}</Link> for per-model breakdown, probes, and recent
        events.
      </p>
    </section>
  )
}
