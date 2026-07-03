/** Vite-backed feature toggles for Lenses Studio (build-time). */

export function blueprintsWizardFeatureEnabled(): boolean {
  const v = import.meta.env.VITE_EXPERIMENTAL_BLUEPRINTS_WIZARD
  if (v === 'false' || v === '0') return false
  return true
}

/** Autonomy maturity panel — default off; server also gates via ``LENSES_EXPERIMENTAL_AUTONOMY_MATURITY``. */
export function autonomyMaturityFeatureEnabled(): boolean {
  const v = import.meta.env.VITE_EXPERIMENTAL_AUTONOMY_MATURITY
  if (v === 'true' || v === '1' || v === 'yes' || v === 'on') return true
  return false
}

/** Opt-in client sends for wizard telemetry POST (server also needs ``LENSES_BLUEPRINTS_WIZARD_TELEMETRY``). */
export function blueprintsWizardTelemetryClientEnabled(): boolean {
  const v = import.meta.env.VITE_BLUEPRINTS_WIZARD_TELEMETRY
  if (v === 'true' || v === '1' || v === 'yes' || v === 'on') return true
  return false
}
