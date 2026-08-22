import { museumDataUrl, museumFileForApiPath } from './staticMuseum'

export class ApiError extends Error {
  readonly status: number
  /** Raw response body or diagnostic text — for “Show technical details” only */
  readonly technicalNote: string | null

  constructor(message: string, status: number, technicalNote?: string | null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.technicalNote = technicalNote != null && technicalNote.trim() ? technicalNote.trim() : null
  }
}

function friendlyHttpStatusLine(status: number): string {
  switch (status) {
    case 400:
      return 'Lenses could not process this request.'
    case 401:
    case 403:
      return 'You don’t have access to this data or action in Lenses.'
    case 404:
      return 'Lenses could not find this item. It may have moved, or your workspace may need a fresh scan.'
    case 408:
      return 'The request timed out before Lenses finished.'
    case 429:
      return 'Lenses is busy right now. Try again in a moment.'
    case 502:
    case 503:
    case 504:
      return 'Lenses is temporarily unavailable. Check that the workspace app is running, then try again.'
    default:
      if (status >= 500) return 'Lenses hit a problem loading this data. Try again shortly.'
      return 'Something went wrong talking to Lenses.'
  }
}

function technicalNoteFromParsedBody(_status: number, parsed: unknown, rawText: string): string {
  const bits: string[] = []
  if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
    const o = parsed as Record<string, unknown>
    const err = o.error != null ? String(o.error) : ''
    const det = o.detail != null ? String(o.detail) : o.message != null ? String(o.message) : ''
    if (err) bits.push(`code: ${err}`)
    if (det) bits.push(`detail: ${det}`)
  }
  const structured = bits.join(' · ')
  if (structured) return structured.length > 6000 ? `${structured.slice(0, 5997)}…` : structured
  const t = rawText.trim()
  if (!t) return ''
  return t.length > 6000 ? `${t.slice(0, 5997)}…` : t
}

function throwApiError(status: number, parsed: unknown, rawText: string): never {
  const technical = technicalNoteFromParsedBody(status, parsed, rawText)
  throw new ApiError(friendlyHttpStatusLine(status), status, technical || rawText.trim() || null)
}

const STATIC_MUSEUM = import.meta.env.VITE_STATIC_MUSEUM === 'true'

/**
 * Origin used for `/api` JSON calls from the browser (same tab, or ``VITE_LENSES_API_BASE``).
 * Use in operator hints (curl, “open Studio”) so copy stays aligned with {@link apiUrl}.
 */
export function resolveLensesJsonApiOrigin(
  viteLensesApiBase: string | undefined,
  pageOrigin: string,
): string {
  const raw = (viteLensesApiBase ?? '').trim().replace(/\/$/, '')
  if (raw) {
    try {
      const withScheme = /^[a-z][a-z0-9+.-]*:\/\//i.test(raw) ? raw : `http://${raw}`
      return new URL(withScheme).origin
    } catch {
      return pageOrigin || ''
    }
  }
  return pageOrigin || ''
}

/** In the browser: {@link resolveLensesJsonApiOrigin} with ``import.meta.env`` and ``window.location.origin``. */
export function lensesJsonApiOrigin(): string {
  if (typeof window === 'undefined') return ''
  return resolveLensesJsonApiOrigin(
    import.meta.env.VITE_LENSES_API_BASE as string | undefined,
    window.location.origin,
  )
}

/**
 * Resolve the JSON API URL. Default is **same-origin** `/api/...` so:
 * - Production Studio on the Lenses server (`/studio/` + `/api/` on one host) works.
 * - Vite `npm run dev` / `vite preview` use `vite.config.ts` **proxy** of `/api` to the Python app
 *   (avoids hard-coding a port and 404s when Lenses runs on another port or only the dev server handles `/api`).
 * Set **`VITE_LENSES_API_BASE`** at build time when the SPA is hosted separately from the API.
 */
/** When the guest SPA is served under ``/stickerboard/`` (leo tunnel), call ``/stickerboard/api/…``. */
export function stickerboardApiPrefix(): string {
  if (typeof window === 'undefined') return ''
  const p = window.location.pathname
  if (p === '/stickerboard' || p.startsWith('/stickerboard/')) return '/stickerboard'
  return ''
}

/** Same path prefix as JSON ``fetch`` — use for ``<a href>`` OIDC login on public hosts. */
export function apiPath(path: string): string {
  const prefix = stickerboardApiPrefix()
  return prefix ? `${prefix}${path}` : path
}

function apiUrl(path: string): string {
  if (STATIC_MUSEUM) return museumDataUrl(museumFileForApiPath(path))
  const explicit = (import.meta.env.VITE_LENSES_API_BASE as string | undefined)?.trim().replace(/\/$/, '') ?? ''
  if (explicit) return `${explicit}${path}`
  return apiPath(path)
}

export async function apiGetJson<T>(path: string, init?: RequestInit): Promise<T> {
  const url = apiUrl(path)
  const res = await fetch(url, {
    headers: { Accept: 'application/json' },
    credentials: STATIC_MUSEUM ? 'same-origin' : 'include',
    ...init,
  })
  const text = await res.text()
  let parsed: unknown = {}
  try {
    parsed = text ? JSON.parse(text) : {}
  } catch {
    parsed = { raw: text }
  }
  if (!res.ok) {
    throwApiError(res.status, parsed, text)
  }
  return parsed as T
}

/** Binary GET (e.g. staged Cursor Launch Pack zip). Uses same API base as JSON helpers. */
export async function apiGetBlob(path: string, init?: RequestInit): Promise<Blob> {
  if (STATIC_MUSEUM) {
    throw new ApiError('Static museum — binary download requires the live Lenses server.', 400)
  }
  const url = apiUrl(path)
  const res = await fetch(url, {
    method: 'GET',
    credentials: 'include',
    ...init,
  })
  if (!res.ok) {
    const errText = await res.text().catch(() => '')
    throw new ApiError(friendlyHttpStatusLine(res.status), res.status, errText.trim() || null)
  }
  return res.blob()
}

export async function apiPostJson<T>(
  path: string,
  body: unknown,
): Promise<T> {
  if (STATIC_MUSEUM) {
    if (path.includes('/toolset/')) {
      return {
        ok: false,
        error: 'Static museum — running workspace scripts is disabled.',
      } as T
    }
    if (path.split('?')[0] === '/api/llm/chat') {
      return {
        ok: false,
        error: 'static_museum',
        detail: 'LLM chat requires the live Lenses Python server (not the static museum build).',
      } as T
    }
    if (path.split('?')[0] === '/api/sdlc-copilot/chat-async') {
      return {
        ok: true,
        session_id: 'static-museum-copilot-session',
      } as T
    }
    if (path.split('?')[0] === '/api/sdlc-copilot/chat') {
      return {
        ok: true,
        text:
          'Static museum build: grounded Lenses Copilot responses are not generated here. Run the live Lenses Python server for retrieval + LLM.',
        citations: [],
        audit_id: 'static-museum',
        grounding_truncated: false,
        write_proposals: [],
        tool_mode: 'read_only',
        turn_reflection: {
          answered: 'partial',
          confidence: 0.5,
          agent_note: 'Museum build: reflection is static.',
          suggested_follow_up: '',
          adjust_context: false,
          source: 'heuristic',
        },
      } as T
    }
    if (path.split('?')[0] === '/api/sdlc-copilot/topic-archive') {
      return {
        ok: true,
        topics_log: '.lenses-local/copilot-topics.jsonl',
        markdown: null,
      } as T
    }
    if (path.split('?')[0] === '/api/llm/settings') {
      return {
        ok: false,
        error: 'static_museum',
        detail: 'LLM settings require the live Lenses Python server.',
      } as T
    }
    if (path.split('?')[0] === '/api/llm/provider-probe') {
      return {
        ok: true,
        models: ['demo-model-a', 'demo-model-b'],
        healthy: true,
        model_count: 2,
      } as T
    }
    if (path.split('?')[0] === '/api/llm/ollama-action') {
      return {
        ok: false,
        error: 'static_museum',
        detail: 'Ollama model pull/remove requires the live Lenses Python server.',
      } as T
    }
    if (path.split('?')[0] === '/api/forgesdlc-blog/sync') {
      return apiGetJson<T>('/api/forgesdlc-blog')
    }
    if (path.split('?')[0] === '/api/blueprints/wizard/session') {
      return {
        ok: true,
        session_id: 'museum-demo-session',
      } as T
    }
    if (path.split('?')[0].includes('/api/blueprints/wizard/session/') && path.includes('/refine')) {
      return {
        ok: false,
        error: 'static_museum',
        detail:
          'Wizard refine requires the live Lenses Python server (same trust boundary as /api/llm/chat).',
      } as T
    }
    if (path.split('?')[0].includes('/create-repo')) {
      return {
        ok: false,
        error: 'static_museum',
        detail: 'Create repository requires the live Lenses Python server.',
      } as T
    }
    if (path.split('?')[0] === '/api/blueprints/wizard/telemetry') {
      return { ok: true } as T
    }
    if (path.split('?')[0] === '/api/orchestration/seed-demo') {
      return {
        ok: false,
        error: 'static_museum',
        detail: 'Orchestration seed reload requires the live Lenses Python server.',
      } as T
    }
    if (path.split('?')[0] === '/api/llm/routing-preview-draft') {
      return apiGetJson<T>('/api/llm/routing-preview')
    }
    if (path.split('?')[0].includes('/docs-health')) {
      return {
        ok: false,
        error: 'static_museum',
        detail: 'Docs Health scans and sessions require the live Lenses Python workspace server.',
      } as T
    }
    return { ok: true } as T
  }
  const url = apiUrl(path)
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    credentials: 'include',
    body: JSON.stringify(body),
  })
  const text = await res.text()
  let data: unknown = {}
  try {
    data = text ? JSON.parse(text) : {}
  } catch {
    data = { raw: text }
  }
  if (!res.ok) {
    throwApiError(res.status, data, text)
  }
  return data as T
}

export async function apiPutJson<T>(path: string, body: unknown): Promise<T> {
  if (STATIC_MUSEUM) {
    const pathOnly = path.split('?')[0]
    if (pathOnly.startsWith('/api/blueprints/wizard/session/')) {
      return {
        ok: false,
        error: 'static_museum',
        detail: 'Session writes require the live Lenses Python server.',
      } as T
    }
    return { ok: true } as T
  }
  const url = apiUrl(path)
  const res = await fetch(url, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    credentials: 'include',
    body: JSON.stringify(body),
  })
  const text = await res.text()
  let data: unknown = {}
  try {
    data = text ? JSON.parse(text) : {}
  } catch {
    data = { raw: text }
  }
  if (!res.ok) {
    throwApiError(res.status, data, text)
  }
  return data as T
}

export function qs(params: Record<string, string | undefined | null>): string {
  const u = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v != null && v !== '') u.set(k, v)
  }
  const s = u.toString()
  return s ? `?${s}` : ''
}
