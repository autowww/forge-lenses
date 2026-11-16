import { splitThreadKey } from './threadKeyUtils'

export type ChatMessageSourceV1 = {
  pathname: string
  /** React Router `search` (includes leading `?` when non-empty). */
  search: string
  title: string
  hint: string
}

export type ChatThreadMessageV1 = {
  role: 'user' | 'assistant'
  text: string
  usage?: {
    prompt_tokens?: number
    completion_tokens?: number
    total_tokens?: number
  }
  failed?: boolean
  retryPrompt?: string
  /** Present on user turns when we know the Studio page context. */
  source?: ChatMessageSourceV1
}

export type ThreadRecordV1 = {
  messages: ChatThreadMessageV1[]
  updatedAt: number
}

export type ChatThreadsBundleV1 = {
  v: 1
  threads: Record<string, ThreadRecordV1>
}

const STORAGE_BASE = 'lenses.studio.chat_threads_bundle_v1'

/** Stable key for Chat page **linear** mode (not route-scoped threads). */
export const LINEAR_CHAT_THREAD_KEY = '__studio_chat_linear__'

function storageKey(workspaceRoot: string | undefined | null): string {
  const w = (workspaceRoot || '').trim()
  if (!w) return STORAGE_BASE
  return `${STORAGE_BASE}::${encodeURIComponent(w)}`
}

function emptyBundle(): ChatThreadsBundleV1 {
  return { v: 1, threads: {} }
}

export function readThreadsBundle(workspaceRoot: string | undefined | null): ChatThreadsBundleV1 {
  try {
    const raw = localStorage.getItem(storageKey(workspaceRoot))
    if (!raw) return emptyBundle()
    const o = JSON.parse(raw) as unknown
    if (!o || typeof o !== 'object') return emptyBundle()
    const rec = o as Record<string, unknown>
    if (rec.v !== 1 || typeof rec.threads !== 'object' || !rec.threads) return emptyBundle()
    return { v: 1, threads: rec.threads as Record<string, ThreadRecordV1> }
  } catch {
    return emptyBundle()
  }
}

export function readThreadMessages(
  workspaceRoot: string | undefined | null,
  threadKey: string,
): ChatThreadMessageV1[] {
  const t = readThreadsBundle(workspaceRoot).threads[threadKey]
  return Array.isArray(t?.messages) ? t.messages : []
}

export function writeThreadMessages(
  workspaceRoot: string | undefined | null,
  threadKey: string,
  messages: ChatThreadMessageV1[],
): void {
  try {
    const bundle = readThreadsBundle(workspaceRoot)
    bundle.threads[threadKey] = {
      messages,
      updatedAt: Date.now(),
    }
    localStorage.setItem(storageKey(workspaceRoot), JSON.stringify(bundle))
  } catch {
    /* quota / private mode */
  }
}

export function listThreadSummaries(
  workspaceRoot: string | undefined | null,
): { threadKey: string; updatedAt: number; messageCount: number }[] {
  const { threads } = readThreadsBundle(workspaceRoot)
  return Object.entries(threads)
    .map(([threadKey, rec]) => ({
      threadKey,
      updatedAt: typeof rec?.updatedAt === 'number' ? rec.updatedAt : 0,
      messageCount: Array.isArray(rec?.messages) ? rec.messages.length : 0,
    }))
    .sort((a, b) => b.updatedAt - a.updatedAt)
}

/** Title for sidebar / headers from a thread key. */
export function threadTitleFromKey(
  threadKey: string,
  titleFn: (pathname: string, search: string) => string,
): string {
  const { pathname, search } = splitThreadKey(threadKey)
  return titleFn(pathname, search)
}
