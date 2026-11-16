import { LlmSettingsForm } from '../components/LlmSettingsForm'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'
import { AdvancedSurfaceFraming, PageHeader } from '../components/page'
import {
  ADMIN_INSPECT_COPY,
  ADVANCED_SURFACE_FRAMES,
  ROUTE_SUBTITLE,
  STUDIO_VOCAB,
} from '../nav/studioVisibleCopy'

export function LlmSettingsPage() {
  useLensesCopilotPage({ route: 'llm-settings', defaultQuery: ADMIN_INSPECT_COPY.copilotLlmPreferencesPlain })
  return (
    <>
      <PageHeader
        title={STUDIO_VOCAB.llmPreferences}
        purpose="Tell Studio which models may answer you on this computer, then sanity-check with Chat."
        subtitle={ROUTE_SUBTITLE.llmPreferencesUtility}
        secondaryMenuItems={[
          { key: 'fleet', to: '/settings/fleet', label: STUDIO_VOCAB.fleetPreferences },
          { key: 'agent', to: '/settings/agent-runtime', label: STUDIO_VOCAB.agentRuntimeInspect },
        ]}
      />
      <div style={{ marginBottom: '0.75rem' }}>
        <AdvancedSurfaceFraming frame={ADVANCED_SURFACE_FRAMES.llmPreferences} />
      </div>
      <LlmSettingsForm />
    </>
  )
}
