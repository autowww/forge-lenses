/** Curated model ids for AI Setup per-task dropdowns (merged with live catalog from provider-probe). */

const OPENAI_LIKE = {
  chat_assistant: ['gpt-4o-mini', 'gpt-4o', 'gpt-4-turbo', 'o1-mini'],
  search_knowledge: ['gpt-4o-mini', 'gpt-4o', 'gpt-4-turbo'],
  plans_generation: ['gpt-4o', 'gpt-4o-mini', 'o1-mini', 'gpt-4-turbo'],
  site_drafting: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo'],
  code_automation: ['gpt-4o', 'gpt-4o-mini', 'o1-mini', 'gpt-3.5-turbo'],
  extraction_classification: ['gpt-4o-mini', 'gpt-4o', 'gpt-4-turbo'],
  vision_ocr: ['gpt-4o', 'gpt-4o-mini'],
  embeddings_indexing: ['text-embedding-3-small', 'text-embedding-3-large', 'text-embedding-ada-002'],
} as const

const ANTHROPIC: Record<string, readonly string[]> = {
  chat_assistant: ['claude-3-5-haiku-20241022', 'claude-3-5-sonnet-20241022', 'claude-3-opus-20240229'],
  search_knowledge: ['claude-3-5-haiku-20241022', 'claude-3-5-sonnet-20241022'],
  plans_generation: ['claude-3-5-sonnet-20241022', 'claude-3-5-haiku-20241022', 'claude-3-opus-20240229'],
  site_drafting: ['claude-3-5-sonnet-20241022', 'claude-3-5-haiku-20241022'],
  code_automation: ['claude-3-5-sonnet-20241022', 'claude-3-5-haiku-20241022', 'claude-3-opus-20240229'],
  extraction_classification: ['claude-3-5-haiku-20241022', 'claude-3-5-sonnet-20241022'],
  vision_ocr: ['claude-3-5-sonnet-20241022', 'claude-3-5-haiku-20241022'],
  embeddings_indexing: [],
}

const GEMINI: Record<string, readonly string[]> = {
  chat_assistant: ['gemini-2.0-flash', 'gemini-1.5-pro', 'gemini-1.5-flash'],
  search_knowledge: ['gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-1.5-pro'],
  plans_generation: ['gemini-1.5-pro', 'gemini-2.0-flash', 'gemini-1.5-flash'],
  site_drafting: ['gemini-1.5-pro', 'gemini-2.0-flash', 'gemini-1.5-flash'],
  code_automation: ['gemini-1.5-pro', 'gemini-2.0-flash', 'gemini-1.5-flash'],
  extraction_classification: ['gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-1.5-pro'],
  vision_ocr: ['gemini-1.5-pro', 'gemini-2.0-flash', 'gemini-1.5-flash'],
  embeddings_indexing: ['text-embedding-004', 'embedding-001'],
}

const OLLAMA: Record<string, readonly string[]> = {
  chat_assistant: ['llama3.2', 'llama3.1', 'qwen2.5', 'mistral'],
  search_knowledge: ['llama3.2', 'qwen2.5', 'mistral'],
  plans_generation: ['llama3.1', 'qwen2.5', 'llama3.2'],
  site_drafting: ['llama3.1', 'llama3.2', 'mistral'],
  code_automation: ['qwen2.5-coder', 'deepseek-coder-v2', 'codellama', 'llama3.1'],
  extraction_classification: ['llama3.2', 'mistral', 'qwen2.5'],
  vision_ocr: ['llava', 'llama3.2-vision', 'bakllava'],
  embeddings_indexing: ['nomic-embed-text', 'mxbai-embed-large', 'all-minilm'],
}

function listFor(provider: string, taskId: string): readonly string[] {
  const pid = provider.trim()
  const row =
    OPENAI_LIKE[taskId as keyof typeof OPENAI_LIKE] ??
    OPENAI_LIKE.chat_assistant
  if (pid === 'openai' || pid === 'openai_compatible') return row
  if (pid === 'anthropic') return ANTHROPIC[taskId] ?? ANTHROPIC.chat_assistant
  if (pid === 'gemini') return GEMINI[taskId] ?? GEMINI.chat_assistant
  if (pid === 'ollama') return OLLAMA[taskId] ?? OLLAMA.chat_assistant
  return []
}

/** Ordered hints for dropdowns (deduped); not exhaustive — server catalog fills the rest. */
export function suggestedModelsForTask(provider: string, taskId: string): string[] {
  return [...listFor(provider, taskId)]
}

export function mergeModelOptionIds(
  mainModelHint: string,
  taskHints: string[],
  catalog: string[],
  stackValues: string[],
): string[] {
  const seen = new Set<string>()
  const out: string[] = []
  const push = (id: string) => {
    const t = id.trim()
    if (!t || seen.has(t)) return
    seen.add(t)
    out.push(t)
  }
  for (const x of [mainModelHint, ...taskHints, ...stackValues]) push(x)
  const rest = [...catalog].sort((a, b) => a.localeCompare(b))
  for (const x of rest) push(x)
  return out
}
