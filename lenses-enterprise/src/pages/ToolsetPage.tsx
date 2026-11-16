import { Link } from 'react-router-dom'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'
import { WorkspaceStateFallback } from '../components/WorkspaceStateFallback'
import { AdvancedSurfaceFraming, PageHeader, TechnicalDetails } from '../components/page'
import { useWorkspace } from '../context/WorkspaceContext'
import { ADMIN_INSPECT_COPY, ADVANCED_SURFACE_FRAMES, ROUTE_SUBTITLE, STUDIO_VOCAB } from '../nav/studioVisibleCopy'

export function ToolsetPage() {
  useLensesCopilotPage({ route: 'toolset', defaultQuery: ADMIN_INSPECT_COPY.copilotAutomationExplain })
  const { state } = useWorkspace()
  if (!state) return <WorkspaceStateFallback />
  const ts = state.toolset || {}
  const names = ts.root_scripts || []
  const cards = ts.script_cards?.length
    ? ts.script_cards
    : names.map((n: string) => ({ name: n, blurb: '' }))

  return (
    <>
      <PageHeader title={STUDIO_VOCAB.toolset} subtitle={ROUTE_SUBTITLE.toolsetAdvanced} />
      <div style={{ marginBottom: '0.75rem' }}>
        <AdvancedSurfaceFraming frame={ADVANCED_SURFACE_FRAMES.toolset} />
      </div>
      <p className="forge-support" style={{ marginBottom: '0.5rem' }}>
        For OpenAI, Anthropic, Gemini, OpenAI-compatible APIs, and Ollama—including model lists and the quality tier
        slider—use{' '}
        <Link to="/settings/llm">AI Setup</Link>
        . Use the Lenses Copilot rail (right) for this session; leave model override empty in the gears menu to follow
        those workspace defaults.
      </p>
      <TechnicalDetails summary="Script index (inspect)">
        <p className="forge-support" style={{ margin: 0 }}>
          Workspace-root <code>*.sh</code> scripts discovered in the scan—shown as cards below.
        </p>
      </TechnicalDetails>
      <div className="le-card-grid">
        {cards.map((c: { name: string; blurb: string }) => (
          <div key={c.name} className="le-card">
            <h3>{c.name}</h3>
            <p className="forge-support">{c.blurb || 'No description in script comments'}</p>
            <Link className="le-btn le-btn--primary" to={`/toolset/${encodeURIComponent(c.name)}`}>
              Run →
            </Link>
          </div>
        ))}
      </div>
      {cards.length === 0 && <p className="forge-support">No shell scripts at workspace root.</p>}
      <TechnicalDetails summary="Cursor / IDE paths (inspect)">
        <p className="forge-support" style={{ margin: 0 }}>
          {ts.cursor_dir ? <code>{ts.cursor_dir}</code> : 'No .cursor directory at workspace root.'}
        </p>
      </TechnicalDetails>
    </>
  )
}
