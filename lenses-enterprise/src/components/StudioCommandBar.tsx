import { createPortal } from 'react-dom'
import { useCallback, useEffect, useId, useMemo, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { apiGetJson, apiPostJson, qs } from '../api/http'
import { resolveUxFailure } from '../lib/uxPageState'
import type { CommandMode, DoAction, FindResult } from '../commandBar/commandBarTypes'
import {
  buildDoActions,
  buildSuggestionFindResults,
  filterNavResults,
} from '../commandBar/buildContextualCommands'
import { useLensesCopilotPageScope } from '../context/LensesCopilotPageScopeContext'
import { compactRelatedMdPathsForApi } from '../lib/copilotPageEvidence'
import { recordCommandBar, recordCommandBarAskFailure } from '../telemetry/studioTelemetry'
import { STUDIO_VOCAB } from '../nav/studioVisibleCopy'

const PROVIDER_IDS = ['anthropic', 'openai', 'gemini', 'openai_compatible', 'ollama'] as const

type LlmSettingsBrief = {
  ok?: boolean
  settings?: { provider?: string; main_models?: Record<string, string> }
}

const RECENT_KEY = 'lenses.studio.cmdRecent'
const RECENT_MAX = 8

type RecentEntry = { label: string; to: string; t: number }

function readRecent(): RecentEntry[] {
  try {
    const raw = localStorage.getItem(RECENT_KEY)
    if (!raw) return []
    const p = JSON.parse(raw) as RecentEntry[]
    return Array.isArray(p) ? p : []
  } catch {
    return []
  }
}

function pushRecent(entry: RecentEntry) {
  try {
    const cur = readRecent().filter((r) => r.to !== entry.to)
    cur.unshift(entry)
    localStorage.setItem(RECENT_KEY, JSON.stringify(cur.slice(0, RECENT_MAX)))
  } catch {
    /* ignore */
  }
}

function parseProjectSlug(pathname: string): string | undefined {
  const m = pathname.match(/^\/projects\/([^/]+)/)
  return m?.[1] ? decodeURIComponent(m[1]) : undefined
}

function inferCopilotRoute(pathname: string): string {
  const p = pathname || '/'
  if (p.startsWith('/plan')) return 'plan'
  if (p.startsWith('/projects/')) return 'projects'
  if (p.startsWith('/search')) return 'search'
  if (p.startsWith('/chat')) return 'chat'
  if (p.startsWith('/settings/llm')) return 'llm-settings'
  if (p.startsWith('/settings/fleet')) return 'fleet-settings'
  if (p.startsWith('/governance/')) return 'governance'
  if (p.startsWith('/overview/charts')) return 'advanced-reporting'
  if (p.startsWith('/toolset')) return 'toolset'
  if (p.startsWith('/settings/ux-insights')) return 'ux-insights'
  if (
    p.startsWith('/workspace-md') ||
    p.startsWith('/tutorials') ||
    p.startsWith('/view/docs') ||
    p.startsWith('/knowledge/') ||
    p.startsWith('/blueprints/wizard')
  ) {
    return 'knowledge'
  }
  if (p.startsWith('/websites') || p.startsWith('/blog')) return 'publish'
  return 'home'
}

type CopilotUsage = {
  prompt_tokens?: number
  completion_tokens?: number
  total_tokens?: number
}

type CopilotChatRes = {
  ok?: boolean
  text?: string
  model?: string
  usage?: CopilotUsage
  /** Effective routing / resolution (from ``llm_chat`` when the call succeeded). */
  routing?: Record<string, unknown>
  citations?: { id?: number; kind?: string; title?: string; ref?: string; snippet?: string }[]
  grounding_truncated?: boolean
  audit_id?: string
}

type SearchHit = { title?: string; url?: string; path_key?: string }

export function StudioCommandBar({
  initialMode,
  initialQuery,
  onClose,
}: {
  initialMode: CommandMode
  initialQuery: string
  onClose: () => void
}) {
  const dialogId = useId()
  const titleId = useId()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const projectSlug = parseProjectSlug(pathname)
  const pageScope = useLensesCopilotPageScope()

  const [mode, setMode] = useState<CommandMode>(initialMode)
  const [query, setQuery] = useState(initialQuery)
  const [findRows, setFindRows] = useState<FindResult[]>([])
  const [findLoading, setFindLoading] = useState(false)
  const [askOut, setAskOut] = useState<{
    text: string
    citations: NonNullable<CopilotChatRes['citations']>
    truncated?: boolean
    auditId?: string
    provider?: string
    model?: string
    usage?: CopilotUsage
    routingSummary?: string
  } | null>(null)
  const [askLoading, setAskLoading] = useState(false)
  const [askBanner, setAskBanner] = useState<string | null>(null)
  const [noGroundedAnswer, setNoGroundedAnswer] = useState(false)
  const [preview, setPreview] = useState<DoAction | null>(null)

  const findInputRef = useRef<HTMLInputElement>(null)
  const askInputRef = useRef<HTMLTextAreaElement>(null)
  const dialogRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    setMode(initialMode)
    setQuery(initialQuery)
  }, [initialMode, initialQuery])

  useEffect(() => {
    setAskOut(null)
    setAskBanner(null)
    setNoGroundedAnswer(false)
  }, [mode])

  useEffect(() => {
    const t = window.setTimeout(() => {
      if (mode === 'find') findInputRef.current?.focus()
      else if (mode === 'ask') askInputRef.current?.focus()
    }, 30)
    return () => clearTimeout(t)
  }, [mode])

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        e.preventDefault()
        onClose()
      }
    }
    document.addEventListener('keydown', onKey, true)
    return () => document.removeEventListener('keydown', onKey, true)
  }, [onClose])

  /** Basic focus trap inside the command dialog (Tab cycles, Shift+Tab wraps). */
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      const d = dialogRef.current
      if (!d || e.key !== 'Tab' || preview) return
      const focusable = Array.from(
        d.querySelectorAll<HTMLElement>(
          'a[href]:not([disabled]), button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])',
        ),
      ).filter((el) => !el.hasAttribute('disabled') && el.offsetParent !== null)
      if (focusable.length === 0) return
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      const active = document.activeElement
      if (!e.shiftKey && active === last) {
        e.preventDefault()
        first.focus()
      } else if (e.shiftKey && active === first) {
        e.preventDefault()
        last.focus()
      }
    }
    const mountEl = dialogRef.current
    if (!mountEl) return
    mountEl.addEventListener('keydown', onKeyDown)
    return () => mountEl.removeEventListener('keydown', onKeyDown)
  }, [mode, preview])

  const mergeFind = useCallback(
    async (q: string) => {
      const nav = filterNavResults(q)
      const sug = buildSuggestionFindResults(pathname, projectSlug).filter(
        (s) =>
          !q.trim() ||
          `${s.label} ${s.description ?? ''} ${s.askPrefill ?? ''}`
            .toLowerCase()
            .includes(q.trim().toLowerCase()),
      )
      const recent = readRecent()
        .filter((r) => !q.trim() || r.label.toLowerCase().includes(q.trim().toLowerCase()) || r.to.includes(q.trim()))
        .map(
          (r): FindResult => ({
            id: `recent-${r.to}`,
            kind: 'nav',
            label: r.label,
            description: 'Recent',
            to: r.to,
          }),
        )
      const base: FindResult[] = [...recent.slice(0, 3), ...sug.slice(0, 4), ...nav]
      const dedupe = (rows: FindResult[]) => {
        const seen = new Set<string>()
        const out: FindResult[] = []
        for (const r of rows) {
          if (seen.has(r.id)) continue
          seen.add(r.id)
          out.push(r)
        }
        return out
      }

      if (q.trim().length < 2) {
        setFindRows(dedupe(base).slice(0, 14))
        return
      }
      setFindLoading(true)
      try {
        const p = qs({ q: q.trim(), limit: '8', offset: '0' })
        const res = await apiGetJson<{ hits?: SearchHit[] }>(`/api/search${p}`)
        const hits = (res.hits ?? []).map(
          (h, i): FindResult => ({
            id: `hit-${h.path_key ?? i}`,
            kind: 'search_hit',
            label: h.title || h.path_key || 'Hit',
            description: h.url,
            to: h.url && h.url.startsWith('/') ? h.url : undefined,
            href: h.url && (h.url.startsWith('http://') || h.url.startsWith('https://')) ? h.url : undefined,
            external: /^https?:/i.test(h.url || ''),
          }),
        )
        recordCommandBar('find_search_api', { qLen: q.trim().length })
        setFindRows(dedupe([...base.filter((b) => b.kind !== 'search_hit'), ...hits]).slice(0, 16))
      } catch {
        setFindRows(dedupe(base).slice(0, 14))
      } finally {
        setFindLoading(false)
      }
    },
    [pathname, projectSlug],
  )

  useEffect(() => {
    if (mode !== 'find') return
    const delay = query.trim().length >= 2 ? 200 : 0
    const h = window.setTimeout(() => void mergeFind(query), delay)
    return () => clearTimeout(h)
  }, [mode, query, mergeFind])

  const doActions = useMemo(() => buildDoActions(pathname, projectSlug), [pathname, projectSlug])

  function findKindLabel(r: FindResult): string {
    if (r.askPrefill) return 'Ask'
    if (r.kind === 'search_hit') return 'Match'
    if (r.kind === 'nav') return 'Go'
    return 'Shortcut'
  }

  function runFind(r: FindResult) {
    if (r.askPrefill) {
      recordCommandBar('contextual_suggestion', { id: r.id })
      setMode('ask')
      setQuery(r.askPrefill)
      setAskOut(null)
      setAskBanner(null)
      setNoGroundedAnswer(false)
      window.setTimeout(() => askInputRef.current?.focus(), 40)
      return
    }
    recordCommandBar('find_select', { kind: r.kind, id: r.id })
    if (r.to) {
      pushRecent({ label: r.label, to: r.to, t: Date.now() })
      navigate(r.to)
      onClose()
    } else if (r.href) {
      if (r.external) {
        window.open(r.href, '_blank', 'noopener,noreferrer')
      } else {
        navigate(r.href)
      }
      onClose()
    }
  }

  async function runAsk() {
    const text = query.trim()
    if (!text || askLoading) return
    setAskBanner(null)
    setAskOut(null)
    setNoGroundedAnswer(false)
    setAskLoading(true)
    recordCommandBar('ask_send', { route: inferCopilotRoute(pathname) })
    try {
      const [provRes, stRes] = await Promise.all([
        apiGetJson<{ providers?: Record<string, boolean> }>('/api/llm/providers').catch(
          () => ({}) as { providers?: Record<string, boolean> },
        ),
        apiGetJson<LlmSettingsBrief>('/api/llm/settings').catch(() => ({}) as LlmSettingsBrief),
      ])
      const pmap = provRes.providers
      let provider = 'ollama'
      if (pmap) {
        const preferred = (stRes.settings?.provider || '').trim().toLowerCase()
        if (preferred && pmap[preferred]) {
          provider = preferred
        } else {
          const first = PROVIDER_IDS.find((id) => pmap[id])
          if (first) provider = first
        }
      }
      const mo = stRes.settings?.main_models?.[provider]
      const body: Record<string, unknown> = {
        provider,
        message: text,
        refine: false,
        tool_mode: 'read_only',
        route: inferCopilotRoute(pathname),
        studio_task_id: 'search_knowledge',
        project_slug: pageScope.projectSlug ?? projectSlug,
        entity_id: pageScope.entityId || undefined,
        scope_site: pageScope.scopeSite ?? projectSlug ?? undefined,
      }
      const pcs = pageScope.pageContextSummary?.trim()
      if (pcs) body.page_context_summary = pcs
      const mdApi = compactRelatedMdPathsForApi(pageScope.relatedMdRelPaths)
      if (mdApi) body.related_md_rel_paths = mdApi
      if (typeof mo === 'string' && mo.trim()) body.model = mo.trim()
      const res = await apiPostJson<CopilotChatRes>('/api/sdlc-copilot/chat', body)
      if (res.ok && res.text) {
        const cites = res.citations ?? []
        const rout = res.routing
        let routingSummary: string | undefined
        if (rout && typeof rout === 'object') {
          const rs = String((rout as { routing_source?: string }).routing_source || '').trim()
          const rm = String((rout as { routing_model?: string }).routing_model || '').trim()
          const fb = String((rout as { fallback_from?: string }).fallback_from || '').trim()
          const stid = String((rout as { studio_task_id?: string }).studio_task_id || '').trim()
          const bits: string[] = []
          if (rs) bits.push(`routing: ${rs}`)
          if (rm) bits.push(`slot / resolved id: ${rm}`)
          if (fb) bits.push(`fallback from: ${fb}`)
          if (stid) bits.push(`task: ${stid}`)
          routingSummary = bits.length ? bits.join(' · ') : undefined
        }
        const u = res.usage
        setAskOut({
          text: res.text,
          citations: cites,
          truncated: res.grounding_truncated,
          auditId: res.audit_id,
          provider,
          model: typeof res.model === 'string' ? res.model : undefined,
          usage: u && typeof u === 'object' ? u : undefined,
          routingSummary,
        })
        if (!cites.length) {
          setNoGroundedAnswer(true)
          recordCommandBar('ask_no_citations', { route: inferCopilotRoute(pathname) })
        }
      } else {
        setAskBanner(
          'No grounded answer was returned. Rephrase, try header Find for a direct link, or open the Copilot page for a longer thread.',
        )
        setNoGroundedAnswer(true)
        recordCommandBarAskFailure(text)
      }
    } catch (e) {
      const ux = resolveUxFailure(e)
      setAskBanner(ux.description)
      recordCommandBarAskFailure(text)
    } finally {
      setAskLoading(false)
    }
  }

  function runDo(a: DoAction) {
    recordCommandBar('do_action', { id: a.id, kind: a.kind })
    if (a.kind === 'navigate' && a.to) {
      navigate(a.to)
      onClose()
    } else if (a.kind === 'open_advanced' && a.to) {
      navigate(a.to)
      onClose()
    } else if (a.kind === 'copy_draft') {
      setPreview(a)
      recordCommandBar('do_preview', { id: a.id })
    }
  }

  const panel = (
    <div className="le-cmd-backdrop" role="presentation" onClick={onClose}>
      <div
        ref={dialogRef}
        id={dialogId}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="le-cmd-dialog"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="le-cmd-head">
          <h2 id={titleId} className="le-cmd-title">
            Find · Ask · Do
          </h2>
          <p className="le-cmd-kbd-hint forge-support">
            <kbd>Esc</kbd> close · <kbd>Ctrl</kbd>+<kbd>K</kbd> / <kbd>⌘</kbd>+<kbd>K</kbd> opens Find
          </p>
          <button type="button" className="le-cmd-close" aria-label="Close command bar" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="le-cmd-modes" role="tablist" aria-label="Command mode">
          {(['find', 'ask', 'do'] as const).map((m) => (
            <button
              key={m}
              type="button"
              role="tab"
              aria-selected={mode === m}
              aria-controls={`le-cmd-panel-${m}`}
              id={`le-cmd-tab-${m}`}
              className={`le-cmd-mode${mode === m ? ' le-cmd-mode--active' : ''}`}
              onClick={() => {
                setMode(m)
                recordCommandBar('mode_change', { mode: m })
              }}
            >
              {m === 'find' ? 'Find' : m === 'ask' ? 'Ask' : 'Do'}
            </button>
          ))}
        </div>

        {mode === 'find' ? (
          <div id="le-cmd-panel-find" role="tabpanel" aria-labelledby="le-cmd-tab-find">
            <label className="forge-support le-cmd-label" htmlFor="le-cmd-input">
              Find pages, files, and indexed hits — contextual rows open in Ask
            </label>
            <input
              ref={findInputRef}
              id="le-cmd-input"
              className="le-input le-cmd-input"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Type to filter or search…"
              autoComplete="off"
            />
            {findLoading ? <p className="forge-support">Searching…</p> : null}
            <ul className="le-cmd-results" role="listbox" aria-label="Find results">
              {findRows.map((r) => (
                <li key={r.id}>
                  <button type="button" className="le-cmd-result" onClick={() => runFind(r)}>
                    <span className="le-cmd-result__kind">{findKindLabel(r)}</span>
                    <span className="le-cmd-result__main">
                      <span className="le-cmd-result__label">{r.label}</span>
                      {r.description ? <span className="le-cmd-result__desc">{r.description}</span> : null}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
            <p className="forge-support le-cmd-foot">
              <Link
                to="/search"
                onClick={() => {
                  recordCommandBar('command_deep_link', { target: '/search', from: 'find_footer' })
                  onClose()
                }}
              >
                Advanced search (full results)
              </Link>
              {' · '}
              <Link
                to="/chat"
                onClick={() => {
                  recordCommandBar('command_deep_link', { target: '/chat', from: 'find_footer' })
                  onClose()
                }}
              >
                Copilot page (threads and providers)
              </Link>
            </p>
          </div>
        ) : null}

        {mode === 'ask' ? (
          <div id="le-cmd-panel-ask" role="tabpanel" aria-labelledby="le-cmd-tab-ask">
            <label className="forge-support le-cmd-label" htmlFor="le-cmd-ask">
              Ask (read-only, grounded on workspace index and graph)
            </label>
            <textarea
              id="le-cmd-ask"
              ref={askInputRef}
              className="le-input le-cmd-textarea"
              rows={3}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask about this workspace…"
            />
            <div className="le-cmd-row">
              <button type="button" className="le-btn le-btn--primary" disabled={askLoading || !query.trim()} onClick={() => void runAsk()}>
                {askLoading ? 'Thinking…' : 'Ask'}
              </button>
              <Link
                className="le-btn"
                to="/chat"
                onClick={() => {
                  recordCommandBar('command_deep_link', { target: '/chat', from: 'ask_footer' })
                  onClose()
                }}
              >
                Open Copilot page
              </Link>
            </div>
            {askBanner ? <p className="le-cmd-warn">{askBanner}</p> : null}
            {noGroundedAnswer && askOut?.text ? (
              <p className="forge-support">
                No context links were attached — treat the answer as partial. Use Find for a direct hit or open{' '}
                <Link to="/workspace-md" onClick={onClose}>
                  Workspace notes
                </Link>
                .
              </p>
            ) : null}
            {askOut ? (
              <div className="le-cmd-answer">
                <h3 className="le-cmd-answer__h">Answer</h3>
                {askOut.provider || askOut.model || askOut.usage ? (
                  <div className="le-cmd-answer__meta" aria-label="Model and token usage for this reply">
                    <strong>LLM</strong>: {askOut.provider ?? '—'}
                    {askOut.model ? (
                      <>
                        {' '}
                        · <strong>model</strong>: <code className="le-mono">{askOut.model}</code>
                      </>
                    ) : null}
                    {askOut.usage ? (
                      typeof askOut.usage.total_tokens === 'number' ||
                      typeof askOut.usage.prompt_tokens === 'number' ||
                      typeof askOut.usage.completion_tokens === 'number' ? (
                        <>
                          {' '}
                          ·{' '}
                          <strong>tokens</strong>:{' '}
                          {typeof askOut.usage.total_tokens === 'number'
                            ? `${askOut.usage.total_tokens.toLocaleString()} total`
                            : null}
                          {typeof askOut.usage.prompt_tokens === 'number' &&
                          typeof askOut.usage.completion_tokens === 'number' ? (
                            <span className="le-muted">
                              {' '}
                              ({askOut.usage.prompt_tokens.toLocaleString()} in +{' '}
                              {askOut.usage.completion_tokens.toLocaleString()} out)
                            </span>
                          ) : null}
                        </>
                      ) : (
                        <span className="le-muted">
                          {' '}
                          · token usage not reported by this provider for this call
                        </span>
                      )
                    ) : null}
                    {askOut.routingSummary ? (
                      <>
                        <br />
                        <span className="le-muted">{askOut.routingSummary}</span>
                      </>
                    ) : null}
                  </div>
                ) : null}
                <div className="le-cmd-answer__body">{askOut.text}</div>
                {askOut.citations.length > 0 ? (
                  <>
                    <h4 className="le-cmd-answer__subh">Context</h4>
                  <ul className="le-cmd-cites">
                    {askOut.citations.map((c, i) => (
                      <li key={`${c.id}-${i}`}>
                        {c.ref && c.ref.startsWith('/') ? (
                          <Link to={c.ref} onClick={onClose}>
                            {c.title || c.ref}
                          </Link>
                        ) : c.ref && /^https?:\/\//i.test(c.ref) ? (
                          <a href={c.ref} target="_blank" rel="noreferrer">
                            {c.title || c.ref}
                          </a>
                        ) : (
                          <span>
                            {c.title} {c.ref ? <code className="le-mono">{c.ref}</code> : null}
                          </span>
                        )}
                        {c.snippet ? <span className="forge-support"> — {c.snippet.slice(0, 120)}</span> : null}
                      </li>
                    ))}
                  </ul>
                  </>
                ) : null}
                {askOut.auditId ? (
                  <p className="forge-support">
                    Audit <code className="le-mono">{askOut.auditId}</code>
                    {askOut.truncated ? ' · grounding truncated' : null}
                  </p>
                ) : null}
              </div>
            ) : null}
          </div>
        ) : null}

        {mode === 'do' ? (
          <div id="le-cmd-panel-do" role="tabpanel" aria-labelledby="le-cmd-tab-do">
            <p className="forge-support le-cmd-label">
              Safe actions — drafts open a preview; nothing is written until you copy or confirm on the server.
            </p>
            <ul className="le-cmd-do">
              {doActions.map((a) => (
                <li key={a.id}>
                  <button type="button" className="le-cmd-do__btn" onClick={() => runDo(a)}>
                    <strong>{a.label}</strong>
                    {a.description ? <span className="forge-support">{a.description}</span> : null}
                  </button>
                </li>
              ))}
            </ul>
            <p className="forge-support le-cmd-foot">
              <Link to="/toolset" onClick={onClose}>
                {STUDIO_VOCAB.toolset}
              </Link>{' '}
              — open from <strong>Settings (gear)</strong> → {STUDIO_VOCAB.adminInspect} when you need workspace
              scripts.
            </p>
          </div>
        ) : null}
      </div>
    </div>
  )

  const previewModal =
    preview && preview.kind === 'copy_draft' ? (
      <div className="le-cmd-backdrop le-cmd-backdrop--nested" role="presentation" onClick={() => setPreview(null)}>
        <div className="le-cmd-preview" role="dialog" aria-modal="true" aria-label="Draft preview" onClick={(e) => e.stopPropagation()}>
          <h3>{preview.draftTitle}</h3>
          <pre className="le-cmd-preview__pre">{preview.draftBody}</pre>
          <div className="le-cmd-row">
            <button
              type="button"
              className="le-btn le-btn--primary"
              onClick={() => {
                void navigator.clipboard.writeText(preview.draftBody || '')
                recordCommandBar('do_copy', { id: preview.id })
              }}
            >
              Copy to clipboard
            </button>
            <button type="button" className="le-btn" onClick={() => setPreview(null)}>
              Close
            </button>
          </div>
        </div>
      </div>
    ) : null

  if (typeof document === 'undefined') return null

  return createPortal(
    <>
      {panel}
      {previewModal}
    </>,
    document.body,
  )
}
