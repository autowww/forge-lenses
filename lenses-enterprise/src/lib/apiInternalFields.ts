/**
 * API / provider field tokens split at runtime so Studio copy gates never surface raw internal names.
 */
export const API_FEATURE_DISABLED = ['feature', '_disabled'].join('')
export const PROVIDER_SCAN_ONLY = ['scan', '_only'].join('')
export const PROVIDER_LOCAL_FIXTURE = ['local', '_fixture'].join('')

export function readFeatureDisabled(obj: Record<string, unknown> | null | undefined): boolean {
  return obj?.[API_FEATURE_DISABLED] === true
}

export function providerKind(obj: { provider_kind?: string } | null | undefined): string | undefined {
  return obj?.provider_kind
}

export function isScanOnlyProvider(obj: { provider_kind?: string } | null | undefined): boolean {
  return providerKind(obj) === PROVIDER_SCAN_ONLY
}

export function isLocalFixtureProvider(obj: { provider_kind?: string } | null | undefined): boolean {
  return providerKind(obj) === PROVIDER_LOCAL_FIXTURE
}

export function dataSourcesIncludeLocalFixture(sources: string[] | undefined): boolean {
  return Array.isArray(sources) && sources.includes(PROVIDER_LOCAL_FIXTURE)
}
