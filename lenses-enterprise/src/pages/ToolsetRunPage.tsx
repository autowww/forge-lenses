import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { apiPostJson } from '../api/http'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'
import { PageHeader } from '../components/page'
import { ADMIN_INSPECT_COPY, ROUTE_SUBTITLE, STUDIO_VOCAB } from '../nav/studioVisibleCopy'

export function ToolsetRunPage() {
  useLensesCopilotPage({ route: 'toolset-run', defaultQuery: ADMIN_INSPECT_COPY.copilotAutomationExplain })
  const { name = '' } = useParams()
  const decoded = decodeURIComponent(name)
  const [out, setOut] = useState<string>('')
  const [busy, setBusy] = useState(false)

  async function run() {
    setBusy(true)
    setOut('')
    try {
      const r = await apiPostJson<{
        ok?: boolean
        stdout?: string
        stderr?: string
        exit_code?: number
        error?: string
      }>('/api/toolset/run', { script: decoded })
      setOut(
        JSON.stringify(r, null, 2) +
          (r.stdout ? `\n--- stdout ---\n${r.stdout}` : '') +
          (r.stderr ? `\n--- stderr ---\n${r.stderr}` : ''),
      )
    } catch (e) {
      setOut(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <PageHeader
        title={`${STUDIO_VOCAB.automationRun}: ${decoded}`}
        subtitle={ROUTE_SUBTITLE.toolsetAdvanced}
        preface={
          <Link to="/toolset" className="forge-support">
            ← {STUDIO_VOCAB.toolset}
          </Link>
        }
      />
      <p className="forge-support" style={{ marginTop: '-0.35rem' }}>
        {ADMIN_INSPECT_COPY.toolsetPurpose} Output below may include stderr from the host shell.
      </p>
      <button type="button" className="le-btn le-btn--primary" disabled={busy} onClick={() => void run()}>
        {busy ? 'Running…' : 'Run script'}
      </button>
      {out && <pre className="le-preview le-json">{out}</pre>}
    </>
  )
}
