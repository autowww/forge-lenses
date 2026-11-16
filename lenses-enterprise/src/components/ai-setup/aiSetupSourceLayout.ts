/** Browser-only layout for AI Setup “Model sources” (Studio). */

export type AiSetupSourceSectionId = 'cloud' | 'custom' | 'ollama'

export type AiSetupTileDensity = 'compact' | 'hero' | 'advanced'

export type CloudCardId = 'openai' | 'anthropic' | 'gemini' | 'more_providers'

export type AiSetupSourceLayoutV2 = {
  version: 2
  /** Section stack on the page (top = highest). */
  order: AiSetupSourceSectionId[]
  /** Vendor + “more” tile order inside the cloud grid. */
  cloudCardOrder: CloudCardId[]
  /** Per cloud swimlane tile (each vendor + “More” can use a different density). */
  cloudTileDensity: Record<CloudCardId, AiSetupTileDensity>
  customTileDensity: AiSetupTileDensity
  ollamaTileDensity: AiSetupTileDensity
}

const STORAGE_KEY_V2 = 'forge-lenses.studio.ai-setup.model-sources-layout.v2'
const STORAGE_KEY_V1 = 'forge-lenses.studio.ai-setup.model-sources-layout.v1'

const ALL_SECTIONS: AiSetupSourceSectionId[] = ['cloud', 'custom', 'ollama']

const ALL_CLOUD_CARDS: CloudCardId[] = ['openai', 'anthropic', 'gemini', 'more_providers']

export const AI_SETUP_SECTION_SHORT: Record<AiSetupSourceSectionId, string> = {
  cloud: 'Cloud',
  custom: 'Custom',
  ollama: 'Ollama',
}

const DEFAULT_CLOUD_DENSITY: Record<CloudCardId, AiSetupTileDensity> = {
  openai: 'compact',
  anthropic: 'compact',
  gemini: 'compact',
  more_providers: 'compact',
}

export const DEFAULT_AI_SETUP_SOURCE_LAYOUT_V2: AiSetupSourceLayoutV2 = {
  version: 2,
  order: ['cloud', 'custom', 'ollama'],
  cloudCardOrder: [...ALL_CLOUD_CARDS],
  cloudTileDensity: { ...DEFAULT_CLOUD_DENSITY },
  customTileDensity: 'hero',
  ollamaTileDensity: 'advanced',
}

function isSectionId(x: unknown): x is AiSetupSourceSectionId {
  return x === 'cloud' || x === 'custom' || x === 'ollama'
}

function isDensity(x: unknown): x is AiSetupTileDensity {
  return x === 'compact' || x === 'hero' || x === 'advanced'
}

function isCloudCardId(x: unknown): x is CloudCardId {
  return x === 'openai' || x === 'anthropic' || x === 'gemini' || x === 'more_providers'
}

function normalizeSectionOrder(order: AiSetupSourceSectionId[]): AiSetupSourceSectionId[] {
  const parsed = order.filter(isSectionId)
  const missing = ALL_SECTIONS.filter((id) => !parsed.includes(id))
  if (parsed.length === 3) return parsed as AiSetupSourceSectionId[]
  if (parsed.length > 0) return [...parsed, ...missing.filter((id) => !parsed.includes(id))]
  return [...ALL_SECTIONS]
}

function normalizeCloudCardOrder(order: unknown): CloudCardId[] {
  if (!Array.isArray(order)) return [...ALL_CLOUD_CARDS]
  const parsed = order.filter(isCloudCardId)
  const missing = ALL_CLOUD_CARDS.filter((id) => !parsed.includes(id))
  if (parsed.length === ALL_CLOUD_CARDS.length) return parsed as CloudCardId[]
  if (parsed.length > 0) return [...parsed, ...missing.filter((id) => !parsed.includes(id))]
  return [...ALL_CLOUD_CARDS]
}

function migrateV1ToV2(raw: Record<string, unknown>): AiSetupSourceLayoutV2 {
  const order = normalizeSectionOrder(
    Array.isArray(raw.order) ? (raw.order as unknown[]).filter(isSectionId) : ALL_SECTIONS,
  )
  const dIn = raw.densities
  let cloudFallback: AiSetupTileDensity = 'compact'
  let customD: AiSetupTileDensity = 'hero'
  let ollamaD: AiSetupTileDensity = 'advanced'
  if (dIn && typeof dIn === 'object') {
    const o = dIn as Record<string, unknown>
    if (isDensity(o.cloud)) cloudFallback = o.cloud
    if (isDensity(o.custom)) customD = o.custom
    if (isDensity(o.ollama)) ollamaD = o.ollama
  }
  const cloudTileDensity: Record<CloudCardId, AiSetupTileDensity> = { ...DEFAULT_CLOUD_DENSITY }
  for (const id of ALL_CLOUD_CARDS) {
    cloudTileDensity[id] = cloudFallback
  }
  return {
    version: 2,
    order,
    cloudCardOrder: [...ALL_CLOUD_CARDS],
    cloudTileDensity,
    customTileDensity: customD,
    ollamaTileDensity: ollamaD,
  }
}

export function loadAiSetupSourceLayout(): AiSetupSourceLayoutV2 {
  if (typeof window === 'undefined') return DEFAULT_AI_SETUP_SOURCE_LAYOUT_V2
  try {
    const raw2 = window.localStorage.getItem(STORAGE_KEY_V2)
    if (raw2) {
      const j = JSON.parse(raw2) as Record<string, unknown>
      if (Number(j.version) === 2) {
        const order = normalizeSectionOrder(
          Array.isArray(j.order) ? (j.order as unknown[]).filter(isSectionId) : ALL_SECTIONS,
        )
        const cloudCardOrder = normalizeCloudCardOrder(j.cloudCardOrder)
        const cloudTileDensity: Record<CloudCardId, AiSetupTileDensity> = { ...DEFAULT_CLOUD_DENSITY }
        const ctIn = j.cloudTileDensity
        if (ctIn && typeof ctIn === 'object') {
          for (const id of ALL_CLOUD_CARDS) {
            const v = (ctIn as Record<string, unknown>)[id]
            if (isDensity(v)) cloudTileDensity[id] = v
          }
        }
        return {
          version: 2,
          order,
          cloudCardOrder,
          cloudTileDensity,
          customTileDensity: isDensity(j.customTileDensity) ? j.customTileDensity : DEFAULT_AI_SETUP_SOURCE_LAYOUT_V2.customTileDensity,
          ollamaTileDensity: isDensity(j.ollamaTileDensity) ? j.ollamaTileDensity : DEFAULT_AI_SETUP_SOURCE_LAYOUT_V2.ollamaTileDensity,
        }
      }
    }
    const raw1 = window.localStorage.getItem(STORAGE_KEY_V1)
    if (raw1) {
      const j = JSON.parse(raw1) as Record<string, unknown>
      return migrateV1ToV2(j)
    }
  } catch {
    return DEFAULT_AI_SETUP_SOURCE_LAYOUT_V2
  }
  return DEFAULT_AI_SETUP_SOURCE_LAYOUT_V2
}

export function saveAiSetupSourceLayout(layout: AiSetupSourceLayoutV2): void {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(STORAGE_KEY_V2, JSON.stringify(layout))
  } catch {
    /* quota / private mode */
  }
}

/** Section stripe: hue by family (cloud=blue, custom=mint, local=gray); strength falls with rank on the page. */
export function aiSetupSectionStripeCss(sectionId: AiSetupSourceSectionId, sectionRank: number): string {
  const steps = Math.max(ALL_SECTIONS.length - 1, 1)
  const t = sectionRank / steps
  const alpha = Math.max(0.32, 0.92 - t * 0.48)
  if (sectionId === 'cloud') return `rgba(88, 145, 220, ${alpha})`
  if (sectionId === 'custom') return `rgba(125, 195, 165, ${alpha})`
  return `rgba(138, 146, 158, ${alpha})`
}

/** Per hosted-vendor card: blue family; higher rank (first in cloud order) = stronger. */
export function aiSetupCloudCardStripeCss(cardRank: number, totalCards: number): string {
  const steps = Math.max(totalCards - 1, 1)
  const t = cardRank / steps
  const alpha = Math.max(0.22, 0.88 - t * 0.55)
  return `rgba(88, 145, 220, ${alpha})`
}
