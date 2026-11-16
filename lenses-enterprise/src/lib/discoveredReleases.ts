import { apiGetJson } from '../api/http'
import { readFeatureDisabled } from './apiInternalFields'

export type DiscoveredRelease = {
  id: string
  display_name: string
}

const DEMO_RELEASE_IDS = ['ogs:demo:release:v1.4.0', 'ogs:demo:release:v1.5.0']

/** Collect release entities from the orchestration graph (assay packets, trace, known demos). */
export async function fetchDiscoveredReleases(): Promise<DiscoveredRelease[]> {
  const seen = new Map<string, DiscoveredRelease>()

  const add = (id: string, display_name?: string) => {
    const key = id.trim()
    if (!key || seen.has(key)) return
    seen.set(key, { id: key, display_name: (display_name || key).trim() || key })
  }

  try {
    const ap = await apiGetJson<{ ok?: boolean; packets?: { id: string; display_name?: string }[] }>(
      '/api/assay-packets',
    )
    if (!ap.ok && readFeatureDisabled(ap as Record<string, unknown>)) {
      // graph off — fall through to demos only
    } else {
      for (const p of ap.packets ?? []) {
        try {
          const view = await apiGetJson<{
            sections?: { release_candidates?: string[] }
            packet?: { payload?: { primary_release_id?: string } }
          }>(`/api/assay-packets/${encodeURIComponent(p.id)}`)
          for (const rid of view.sections?.release_candidates ?? []) {
            add(rid)
          }
          const primary = view.packet?.payload?.primary_release_id
          if (primary) add(primary)
        } catch {
          /* skip packet */
        }
      }
    }
  } catch {
    /* assay list unavailable */
  }

  try {
    const trace = await apiGetJson<{ nodes?: { id?: string; kind?: string; display_name?: string }[] }>(
      '/api/orchestration/trace?root=ogs:demo:story:rate-limit-auth&direction=both&max_depth=12&max_nodes=400',
    )
    for (const n of trace.nodes ?? []) {
      if (n.kind === 'release' && n.id) add(n.id, n.display_name)
    }
  } catch {
    /* trace unavailable */
  }

  for (const id of DEMO_RELEASE_IDS) {
    try {
      const b = await apiGetJson<{ entity?: { id?: string; display_name?: string } }>(
        `/api/methodology/records/${encodeURIComponent(id)}`,
      )
      if (b.entity?.id) add(b.entity.id, b.entity.display_name)
      else add(id)
    } catch {
      add(id)
    }
  }

  return [...seen.values()].sort((a, b) => a.display_name.localeCompare(b.display_name, undefined, { sensitivity: 'base' }))
}
