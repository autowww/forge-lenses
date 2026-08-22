/**
 * Lightweight client-side UX telemetry: in-memory ring buffer + rolling counters.
 * No third-party analytics; data stays in the browser unless the team opens UX insights or reads the buffer.
 *
 * Enable verbose console logging: localStorage `lenses_studio_telemetry_console=1`
 * (also on automatically in Vite dev unless disabled).
 */
import type { NavMode } from '../nav/workspaceLensCookie'

/** Mirrors `StatePanelVariant` — duplicated to avoid telemetry → UI import cycles. */
type TelemetryStatePanelVariant =
  | 'loading'
  | 'empty'
  | 'error'
  | 'invalid'
  | 'stale'
  | 'legacy'
  | 'unavailable'
  | 'not_configured'
  | 'permission'
  | 'beta'

export type StudioTelemetryNavIntent = 'native' | 'shortcut' | 'classic' | 'external'

export type StudioTelemetryEvent = {
  t: number
  name: string
  payload?: Record<string, unknown>
}

const MAX_EVENTS = 280

const buffer: StudioTelemetryEvent[] = []

function pushEvent(ev: StudioTelemetryEvent) {
  buffer.push(ev)
  if (buffer.length > MAX_EVENTS) buffer.splice(0, buffer.length - MAX_EVENTS)
}

const routeCounts = new Map<string, number>()
const sidebarIntentCounts = new Map<StudioTelemetryNavIntent, number>()
const statePanelCounts = new Map<string, number>()
const failureCounts = new Map<string, number>()
const commandBarActionCounts = new Map<string, number>()
const commandBarAskFailQueries = new Map<string, number>()
const commandBarContextualSuggestionIds = new Map<string, number>()
const commandBarDeepLinkCounts = new Map<string, number>()
const tourStepCounts = new Map<string, number>()
const wizardStepCounts = new Map<string, number>()

function bumpCount(map: Map<string, number>, key: string) {
  map.set(key, (map.get(key) ?? 0) + 1)
}

function consoleEnabled(): boolean {
  try {
    if (import.meta.env.DEV) {
      if (typeof localStorage !== 'undefined' && localStorage.getItem('lenses_studio_telemetry_console') === '0') {
        return false
      }
      return true
    }
    return typeof localStorage !== 'undefined' && localStorage.getItem('lenses_studio_telemetry_console') === '1'
  } catch {
    return false
  }
}

function debugLog(ev: StudioTelemetryEvent) {
  if (!consoleEnabled()) return
  console.debug('[studio-ux]', ev.name, ev.payload ?? {})
}

/** Optional hook for E2E or manual inspection (set in dev in StudioRouteListener). */
declare global {
  interface Window {
    __FORGE_STUDIO_TELEMETRY__?: {
      getSnapshot: typeof getStudioTelemetrySnapshot
      clear: typeof clearStudioTelemetry
    }
  }
}

export function recordStudioEvent(name: string, payload?: Record<string, unknown>) {
  const ev: StudioTelemetryEvent = { t: Date.now(), name, payload }
  pushEvent(ev)
  debugLog(ev)

  if (name === 'route_view' && payload?.pathname != null) {
    const p = String(payload.pathname)
    routeCounts.set(p, (routeCounts.get(p) ?? 0) + 1)
  }
  if (name === 'sidebar_nav' && payload?.intent != null) {
    const intent = payload.intent as StudioTelemetryNavIntent
    if (intent === 'native' || intent === 'shortcut' || intent === 'classic' || intent === 'external') {
      sidebarIntentCounts.set(intent, (sidebarIntentCounts.get(intent) ?? 0) + 1)
    }
  }
  if (name === 'state_panel' && payload?.key != null) {
    const k = String(payload.key)
    statePanelCounts.set(k, (statePanelCounts.get(k) ?? 0) + 1)
  }
  if (name === 'page_failure' && payload?.context != null) {
    const c = String(payload.context)
    failureCounts.set(c, (failureCounts.get(c) ?? 0) + 1)
  }
  if (name === 'tour_step' && payload?.stepId != null) {
    const k = `${String(payload.stepId)}:${String(payload.action ?? 'view')}`
    bumpCount(tourStepCounts, k)
  }
  if (name === 'first_run_wizard_step' && payload?.step != null) {
    const k = `step-${String(payload.step)}:${String(payload.action ?? 'view')}`
    bumpCount(wizardStepCounts, k)
  }
  if (name === 'command_bar' && payload?.action != null) {
    const a = String(payload.action)
    commandBarActionCounts.set(a, (commandBarActionCounts.get(a) ?? 0) + 1)
    if (a === 'contextual_suggestion' && payload.id != null) {
      const id = String(payload.id)
      commandBarContextualSuggestionIds.set(id, (commandBarContextualSuggestionIds.get(id) ?? 0) + 1)
    }
    if (a === 'command_deep_link' && payload.target != null && payload.from != null) {
      const k = `${String(payload.from)}→${String(payload.target)}`
      commandBarDeepLinkCounts.set(k, (commandBarDeepLinkCounts.get(k) ?? 0) + 1)
    }
    if (a === 'page_tooling' && payload.surface != null && payload.choice != null) {
      const k = `page:${String(payload.surface)}:${String(payload.choice)}`
      commandBarDeepLinkCounts.set(k, (commandBarDeepLinkCounts.get(k) ?? 0) + 1)
    }
  }
}

/** Command bar (Find / Ask / Do) — action is a short verb: open, close, find_run, ask_send, … */
export function recordCommandBar(action: string, payload?: Record<string, unknown>) {
  recordStudioEvent('command_bar', { action, ...payload })
}

export function recordCommandBarAskFailure(query: string) {
  const q = query.trim().slice(0, 200) || '(empty)'
  commandBarAskFailQueries.set(q, (commandBarAskFailQueries.get(q) ?? 0) + 1)
  recordStudioEvent('command_bar', { action: 'ask_failed', query: q })
}

/** Page-level buttons vs header command (Search / Copilot insight rows, forms, etc.). */
export function recordPageToolingChoice(surface: string, choice: string) {
  recordStudioEvent('command_bar', { action: 'page_tooling', surface, choice })
}

export function recordLensChange(from: NavMode, to: NavMode) {
  recordStudioEvent('lens_change', { from, to })
}

export function recordSidebarNavClick(intent: StudioTelemetryNavIntent, label: string, target: string) {
  recordStudioEvent('sidebar_nav', { intent, label, target })
}

export function recordStatePanelView(variant: TelemetryStatePanelVariant, telemetryTag: string) {
  if (variant === 'loading') return
  recordStudioEvent('state_panel', { key: `${variant}:${telemetryTag}`, variant, tag: telemetryTag })
}

export function recordPageFailure(context: string, detail?: string) {
  recordStudioEvent('page_failure', { context, detail })
}

/** In-app tour step impressions — view, next, finish, dismiss. */
export function recordTourStep(stepId: string, action: 'view' | 'next' | 'finish' | 'dismiss' = 'view') {
  recordStudioEvent('tour_step', { stepId, action })
}

/** First-run wizard funnel — step number and action (next, skip, finish). */
export function recordFirstRunWizardStep(step: number, action: string) {
  recordStudioEvent('first_run_wizard_step', { step, action })
}

export type StudioTelemetrySnapshot = {
  generatedAt: number
  events: StudioTelemetryEvent[]
  aggregates: {
    routeViews: Record<string, number>
    sidebarNavByIntent: Record<string, number>
    statePanels: Record<string, number>
    pageFailures: Record<string, number>
    commandBarActions: Record<string, number>
    commandBarAskFailures: Record<string, number>
    commandBarContextualSuggestions: Record<string, number>
    commandBarDeepLinks: Record<string, number>
    tourSteps: Record<string, number>
    firstRunWizardSteps: Record<string, number>
  }
}

export function getStudioTelemetrySnapshot(): StudioTelemetrySnapshot {
  return {
    generatedAt: Date.now(),
    events: [...buffer],
    aggregates: {
      routeViews: Object.fromEntries(routeCounts),
      sidebarNavByIntent: Object.fromEntries(sidebarIntentCounts),
      statePanels: Object.fromEntries(statePanelCounts),
      pageFailures: Object.fromEntries(failureCounts),
      commandBarActions: Object.fromEntries(commandBarActionCounts),
      commandBarAskFailures: Object.fromEntries(commandBarAskFailQueries),
      commandBarContextualSuggestions: Object.fromEntries(commandBarContextualSuggestionIds),
      commandBarDeepLinks: Object.fromEntries(commandBarDeepLinkCounts),
      tourSteps: Object.fromEntries(tourStepCounts),
      firstRunWizardSteps: Object.fromEntries(wizardStepCounts),
    },
  }
}

export function clearStudioTelemetry() {
  buffer.length = 0
  routeCounts.clear()
  sidebarIntentCounts.clear()
  statePanelCounts.clear()
  failureCounts.clear()
  commandBarActionCounts.clear()
  commandBarAskFailQueries.clear()
  commandBarContextualSuggestionIds.clear()
  commandBarDeepLinkCounts.clear()
  tourStepCounts.clear()
  wizardStepCounts.clear()
}

export function installGlobalTelemetryApi() {
  if (typeof window === 'undefined') return
  window.__FORGE_STUDIO_TELEMETRY__ = {
    getSnapshot: getStudioTelemetrySnapshot,
    clear: clearStudioTelemetry,
  }
}

/** Scorecard: shortcut share of sidebar clicks (0–1), or null if no data. */
export function getShortcutEntryShare(snapshot: StudioTelemetrySnapshot): number | null {
  const s = snapshot.aggregates.sidebarNavByIntent
  const total = (s.native ?? 0) + (s.shortcut ?? 0) + (s.classic ?? 0) + (s.external ?? 0)
  if (total === 0) return null
  return (s.shortcut ?? 0) / total
}
