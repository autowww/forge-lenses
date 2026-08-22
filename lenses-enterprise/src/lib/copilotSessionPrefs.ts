/**
 * Persist Lenses Copilot rail / panel session choices (provider, optional model, tool mode)
 * in ``localStorage``, scoped by workspace root when known.
 */

const STORAGE_V1 = 'lenses.studio.copilot_session_v1'
const FULL_CHAT_V1 = 'lenses.studio.full_chat_session_v1'

export type CopilotSessionPrefsV1 = {
  provider?: string
  /** Empty string = use AI Setup default for the provider. */
  model?: string
  toolMode?: 'read_only' | 'propose_writes'
}

function storageKey(
  workspaceRoot: string | undefined | null,
  base: typeof STORAGE_V1 | typeof FULL_CHAT_V1 = STORAGE_V1,
): string {
  const w = (workspaceRoot || '').trim()
  if (!w) return base
  return `${base}::${encodeURIComponent(w)}`
}

const VALID_TOOL: Record<string, true> = { read_only: true, propose_writes: true }

function coerce(raw: unknown): CopilotSessionPrefsV1 | null {
  if (!raw || typeof raw !== 'object') return null
  const o = raw as Record<string, unknown>
  const out: CopilotSessionPrefsV1 = {}
  if (typeof o.provider === 'string' && o.provider.trim()) out.provider = o.provider.trim().toLowerCase()
  if (typeof o.model === 'string') out.model = o.model
  const tm = typeof o.toolMode === 'string' ? o.toolMode.trim() : ''
  if (tm && VALID_TOOL[tm]) out.toolMode = tm as 'read_only' | 'propose_writes'
  return Object.keys(out).length ? out : null
}

export function readCopilotSessionPrefs(workspaceRoot: string | undefined | null): CopilotSessionPrefsV1 | null {
  try {
    const raw = localStorage.getItem(storageKey(workspaceRoot, STORAGE_V1))
    if (!raw) return null
    return coerce(JSON.parse(raw))
  } catch {
    return null
  }
}

/** Prefer scoped prefs; fall back to unscoped legacy key (pre–workspace-scoped saves). */
export function readCopilotSessionPrefsWithFallback(workspaceRoot: string | undefined | null): CopilotSessionPrefsV1 | null {
  const r = (workspaceRoot || '').trim()
  if (r) {
    const scoped = readCopilotSessionPrefs(r)
    if (scoped) return scoped
  }
  return readCopilotSessionPrefs(undefined)
}

export function writeCopilotSessionPrefs(
  workspaceRoot: string | undefined | null,
  prefs: CopilotSessionPrefsV1,
): void {
  try {
    const cur = readCopilotSessionPrefsWithFallback(workspaceRoot) || {}
    const next: CopilotSessionPrefsV1 = { ...cur, ...prefs }
    localStorage.setItem(storageKey(workspaceRoot, STORAGE_V1), JSON.stringify(next))
  } catch {
    /* quota / private mode */
  }
}

export type FullChatSessionPrefsV1 = Pick<CopilotSessionPrefsV1, 'provider' | 'model'>

function readFullChatRaw(workspaceRoot: string | undefined | null): FullChatSessionPrefsV1 | null {
  try {
    const raw = localStorage.getItem(storageKey(workspaceRoot, FULL_CHAT_V1))
    if (!raw) return null
    return coerce(JSON.parse(raw)) as FullChatSessionPrefsV1 | null
  } catch {
    return null
  }
}

export function readFullChatSessionPrefsWithFallback(
  workspaceRoot: string | undefined | null,
): FullChatSessionPrefsV1 | null {
  const r = (workspaceRoot || '').trim()
  if (r) {
    const scoped = readFullChatRaw(r)
    if (scoped) return scoped
  }
  return readFullChatRaw(undefined)
}

export function writeFullChatSessionPrefs(
  workspaceRoot: string | undefined | null,
  prefs: FullChatSessionPrefsV1,
): void {
  try {
    const cur = readFullChatSessionPrefsWithFallback(workspaceRoot) || {}
    const next = { ...cur, ...prefs }
    localStorage.setItem(storageKey(workspaceRoot, FULL_CHAT_V1), JSON.stringify(next))
  } catch {
    /* quota / private mode */
  }
}

/**
 * Merge **Copilot rail** + **Chat page** prefs so either surface restores the last choice.
 * Copilot wins on conflicts (rail is the usual place users pick provider/model).
 */
export function readStudioLlmPrefsForHydration(workspaceRoot: string | undefined | null): CopilotSessionPrefsV1 | null {
  const cp = readCopilotSessionPrefsWithFallback(workspaceRoot)
  const fc = readFullChatSessionPrefsWithFallback(workspaceRoot)
  const provider = (cp?.provider || fc?.provider || '').trim().toLowerCase()
  let model: string | undefined
  const cpHasModel = Boolean(cp && Object.prototype.hasOwnProperty.call(cp, 'model') && typeof cp.model === 'string')
  const fcHasModel = Boolean(fc && Object.prototype.hasOwnProperty.call(fc, 'model') && typeof fc.model === 'string')
  const cpModel = cpHasModel && cp ? cp.model : undefined
  const fcModel = fcHasModel && fc ? fc.model : undefined
  const cpModelUseful = Boolean((cpModel ?? '').trim())
  const fcModelUseful = Boolean((fcModel ?? '').trim())
  // Prefer a non-empty override so the rail’s “use default” (empty) does not wipe Chat’s saved model id.
  if (cpModelUseful) model = cpModel
  else if (fcModelUseful) model = fcModel
  else if (cpHasModel) model = cpModel
  else if (fcHasModel) model = fcModel
  const toolMode =
    cp?.toolMode === 'read_only' || cp?.toolMode === 'propose_writes' ? cp.toolMode : undefined
  const out: CopilotSessionPrefsV1 = {}
  if (provider) out.provider = provider
  if (model !== undefined) out.model = model
  if (toolMode) out.toolMode = toolMode
  return Object.keys(out).length ? out : null
}

/** Persist provider/model to **both** storage keys so Chat and Copilot rail stay aligned. */
export function writeMirroredLlmSessionPrefs(
  workspaceRoot: string | undefined | null,
  prefs: CopilotSessionPrefsV1,
): void {
  writeCopilotSessionPrefs(workspaceRoot, prefs)
  const next = readCopilotSessionPrefsWithFallback(workspaceRoot) || {}
  const fc: FullChatSessionPrefsV1 = {}
  if (typeof next.provider === 'string' && next.provider.trim()) {
    fc.provider = next.provider.trim().toLowerCase()
  }
  if (Object.prototype.hasOwnProperty.call(next, 'model') && typeof next.model === 'string') {
    fc.model = next.model
  }
  if (fc.provider !== undefined || fc.model !== undefined) {
    writeFullChatSessionPrefs(workspaceRoot, fc)
  }
}

export type CopilotFailureFields = {
  detail?: string | null
  error?: string | null
}

/** Turn API failure fields into a user-facing Copilot error (gateway hints when recognizable). */
export function formatCopilotFailureMessage(
  res: CopilotFailureFields,
  fallback: string,
): string {
  const parts = [res.detail, res.error].filter(
    (x) => typeof x === 'string' && x.trim(),
  ) as string[]
  const raw = parts.length ? parts.join(' · ') : fallback
  const lower = raw.toLowerCase()
  if (
    lower.includes('llama runner') ||
    lower.includes('runner process has terminated') ||
    (res.error === 'llm_provider_error' && lower.includes('terminated'))
  ) {
    return (
      `${raw} — the custom gateway model runner crashed. ` +
      'In Copilot settings (gear), clear Model to use your AI Setup default, or pick a stable id ' +
      '(e.g. ctx-unlim-qwen3-1p7b:latest). ctx-unlim-granite41-3b:latest often fails on this gateway.'
    )
  }
  if (res.error === 'stream_timeout' || lower.includes('stream timed out')) {
    return (
      `${raw} — the server stopped waiting for Copilot to finish. ` +
      'Slow custom gateways may need several minutes on large workspace questions; retry or use a faster model.'
    )
  }
  return raw
}

/** Gateway models that crash the Ollama runner on granite.forgedc.net (do not persist as Copilot override). */
export function isKnownUnstableOpenAiCompatModel(modelId: string): boolean {
  const id = modelId.trim().toLowerCase()
  if (!id) return false
  if (/granite41-3b/i.test(id)) return true
  if (id === 'ctx-unlim-granite41-3b:latest') return true
  return false
}

/**
 * Normalize a saved Copilot model override: drop empty, known-crash ids, and redundant copies of AI Setup main.
 */
export function sanitizeStudioModelOverride(
  model: string | undefined,
  setupMainModel?: string,
): string {
  const m = (model ?? '').trim()
  if (!m) return ''
  if (isKnownUnstableOpenAiCompatModel(m)) return ''
  const main = (setupMainModel ?? '').trim()
  if (main && m === main) return ''
  return m
}

/** Prefer qwen / non-granite ids when AI Setup has no main model for openai_compatible. */
export function pickOpenAiCompatFallbackModel(modelIds: string[]): string | undefined {
  const sorted = [...new Set(modelIds.map((x) => x.trim()).filter(Boolean))].sort((a, b) =>
    a.localeCompare(b),
  )
  if (!sorted.length) return undefined
  const qwen = sorted.find((id) => /qwen/i.test(id))
  if (qwen) return qwen
  const nonGranite = sorted.find((id) => !/granite/i.test(id))
  return nonGranite ?? sorted[0]
}
