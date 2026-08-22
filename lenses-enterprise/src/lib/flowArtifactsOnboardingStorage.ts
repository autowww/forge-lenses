/**
 * Local persistence for Flow vs Artifacts onboarding (workspace overview + deep links).
 * Migrates legacy `lenses_studio_onboarding_lens_dismissed` → banner dismissed (chip shown).
 */

const LEGACY_DISMISS = 'lenses_studio_onboarding_lens_dismissed'
const BANNER_DISMISSED = 'lenses_studio_flow_artifacts_banner_dismissed'
const CHIP_OVERVIEW_HIDDEN = 'lenses_studio_flow_artifacts_chip_overview_hidden'

function safeGet(key: string): string | null {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}

function safeSet(key: string, value: string) {
  try {
    localStorage.setItem(key, value)
  } catch {
    /* quota / private mode */
  }
}

/**
 * Whether the large Flow vs Artifacts panel should stay collapsed on Home.
 * UX1 default: treat as dismissed when unset so the overview is not dominated by lens chrome;
 * reopen via `/?studioHelp=lens`, the compact chip, Settings, or UX insights.
 */
export function readFlowArtifactsBannerDismissed(): boolean {
  if (typeof window === 'undefined') return true
  if (safeGet(BANNER_DISMISSED) === '1') return true
  if (safeGet(LEGACY_DISMISS) === '1') {
    safeSet(BANNER_DISMISSED, '1')
    return true
  }
  if (safeGet(BANNER_DISMISSED) === '0') return false
  return true
}

export function writeFlowArtifactsBannerDismissed() {
  safeSet(BANNER_DISMISSED, '1')
}

/** Dogfood / QA: show the large explainer on Home again until dismissed. */
export function writeFlowArtifactsBannerOptIn() {
  safeSet(BANNER_DISMISSED, '0')
}

/** Compact overview chip hidden (“Don’t show overview hint”). */
export function readFlowArtifactsChipOverviewHidden(): boolean {
  if (typeof window === 'undefined') return false
  return safeGet(CHIP_OVERVIEW_HIDDEN) === '1'
}

export function writeFlowArtifactsChipOverviewHidden() {
  safeSet(CHIP_OVERVIEW_HIDDEN, '1')
}
