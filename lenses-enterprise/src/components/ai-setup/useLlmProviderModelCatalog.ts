import { useEffect, useState } from 'react'
import { apiPostJson } from '../../api/http'

type CatalogState = 'idle' | 'loading' | 'ok' | 'error'

export type LlmProviderModelCatalog = {
  models: string[]
  state: CatalogState
}

const cache = new Map<string, { at: number; models: string[] }>()
const TTL_MS = 45_000

export function useLlmProviderModelCatalog(
  providersMap: Record<string, boolean> | null,
  providerId: string,
): LlmProviderModelCatalog {
  const pid = (providerId || '').trim().toLowerCase()
  const ready = Boolean(pid && providersMap?.[pid])
  const [models, setModels] = useState<string[]>([])
  const [state, setState] = useState<CatalogState>('idle')

  useEffect(() => {
    if (!ready) {
      setModels([])
      setState('idle')
      return
    }
    const now = Date.now()
    const hit = cache.get(pid)
    if (hit && now - hit.at < TTL_MS) {
      setModels(hit.models)
      setState('ok')
      return
    }
    let cancel = false
    setState('loading')
    void apiPostJson<{ ok?: boolean; models?: string[] }>('/api/llm/provider-probe', {
      provider: pid,
      action: 'models',
    })
      .then((out) => {
        if (cancel) return
        if (out.ok && Array.isArray(out.models)) {
          const sorted = [...out.models]
            .map((m) => String(m).trim())
            .filter(Boolean)
            .sort((a, b) => a.localeCompare(b))
          cache.set(pid, { at: Date.now(), models: sorted })
          setModels(sorted)
          setState('ok')
        } else {
          setModels([])
          setState('error')
        }
      })
      .catch(() => {
        if (cancel) return
        setModels([])
        setState('error')
      })
    return () => {
      cancel = true
    }
  }, [pid, ready])

  return { models, state }
}
