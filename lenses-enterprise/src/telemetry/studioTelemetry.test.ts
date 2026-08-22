import { describe, expect, it, beforeEach } from 'vitest'
import {
  clearStudioTelemetry,
  getShortcutEntryShare,
  getStudioTelemetrySnapshot,
  recordCommandBar,
  recordSidebarNavClick,
  recordStudioEvent,
} from './studioTelemetry'

describe('studioTelemetry', () => {
  beforeEach(() => {
    clearStudioTelemetry()
  })

  it('aggregates route_view by pathname', () => {
    recordStudioEvent('route_view', { pathname: '/plan', search: '', lens: 'flow' })
    recordStudioEvent('route_view', { pathname: '/plan', search: '', lens: 'flow' })
    const s = getStudioTelemetrySnapshot()
    expect(s.aggregates.routeViews['/plan']).toBe(2)
  })

  it('computes shortcut share from sidebar_nav intents', () => {
    recordSidebarNavClick('native', 'X', '/plan')
    recordSidebarNavClick('shortcut', 'Y', '/board')
    recordSidebarNavClick('shortcut', 'Z', '/timeline')
    const s = getStudioTelemetrySnapshot()
    expect(getShortcutEntryShare(s)).toBeCloseTo(2 / 3, 5)
  })

  it('clears buffer and aggregates', () => {
    recordStudioEvent('route_view', { pathname: '/', search: '', lens: 'flow' })
    clearStudioTelemetry()
    const s = getStudioTelemetrySnapshot()
    expect(Object.keys(s.aggregates.routeViews)).toHaveLength(0)
    expect(s.events).toHaveLength(0)
  })

  it('aggregates command_bar actions', () => {
    recordCommandBar('open', { mode: 'find' })
    recordCommandBar('open', { mode: 'ask' })
    recordCommandBar('ask_send', { route: 'home' })
    const s = getStudioTelemetrySnapshot()
    expect(s.aggregates.commandBarActions.open).toBe(2)
    expect(s.aggregates.commandBarActions.ask_send).toBe(1)
  })

  it('aggregates contextual suggestions and page tooling', () => {
    recordCommandBar('contextual_suggestion', { id: 'sug-health' })
    recordCommandBar('contextual_suggestion', { id: 'sug-health' })
    recordCommandBar('page_tooling', { surface: 'search_insight', choice: 'header_ask' })
    const s = getStudioTelemetrySnapshot()
    expect(s.aggregates.commandBarContextualSuggestions['sug-health']).toBe(2)
    expect(s.aggregates.commandBarDeepLinks['page:search_insight:header_ask']).toBe(1)
  })
})
