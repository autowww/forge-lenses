import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, apiGetJson } from '../api/http'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'
import { AdvancedSurfaceFraming, PageHeader, StatePanel, TechnicalDetails } from '../components/page'
import { resolveUxFailure, type UxResolvedFailure } from '../lib/uxPageState'
import { ADMIN_INSPECT_COPY, ADVANCED_SURFACE_FRAMES, ROUTE_SUBTITLE } from '../nav/studioVisibleCopy'

type AuditEvent = {
  id?: string
  ts?: string
  kind?: string
  actor?: string | null
  resource?: string
  project_slug?: string | null
  detail?: Record<string, unknown>
}

type AuditRes = {
  ok?: boolean
  events?: AuditEvent[]
  error?: string
}

export function GovernanceAuditPage() {
  useLensesCopilotPage({ route: 'governance-audit', defaultQuery: ADMIN_INSPECT_COPY.copilotAuditDigest })
  const [data, setData] = useState<AuditRes | null>(null)
  const [err, setErr] = useState<UxResolvedFailure | null>(null)
  const [loading, setLoading] = useState(true)
  const [retryNonce, setRetryNonce] = useState(0)

  useEffect(() => {
    let cancel = false
    setLoading(true)
    apiGetJson<AuditRes>('/api/governance/audit?limit=120')
      .then((d) => {
        if (cancel) return
        setData(d)
        setErr(null)
      })
      .catch((e) => {
        if (cancel) return
        if (e instanceof ApiError && e.status === 403) {
          setData({ ok: false, error: 'super_admin_required' })
          setErr(null)
        } else {
          setErr(resolveUxFailure(e))
        }
      })
      .finally(() => {
        if (!cancel) setLoading(false)
      })
    return () => {
      cancel = true
    }
  }, [retryNonce])

  const forbidden = data?.error === 'super_admin_required'

  return (
    <>
      <PageHeader
        title="Audit log"
        preface={
          <Link to="/governance/connectors" className="forge-support">
            ← Connector health
          </Link>
        }
        subtitle={ROUTE_SUBTITLE.governanceAudit}
      />
      <div style={{ marginTop: '-0.35rem', marginBottom: '0.75rem' }}>
        <AdvancedSurfaceFraming frame={ADVANCED_SURFACE_FRAMES.auditLog} />
      </div>
      {loading ? (
        <StatePanel variant="loading" title="Loading audit log" description="Reading recent governance events." />
      ) : null}
      {err ? (
        <StatePanel
          variant="error"
          title={err.title}
          description={err.description}
          technicalDetail={err.technical}
          actions={
            <button type="button" className="le-btn le-btn--primary" onClick={() => setRetryNonce((n) => n + 1)}>
              Retry
            </button>
          }
        />
      ) : null}
      {forbidden ? (
        <StatePanel
          variant="error"
          title="Super admin required"
          description="Only workspace super admins may read governance-audit.jsonl. Sign in with a super_admin account."
        />
      ) : null}
      {!loading && !err && !forbidden && data?.events ? (
        <ul className="le-list" style={{ listStyle: 'none', paddingLeft: 0, fontSize: '0.85rem' }}>
          {data.events
            .slice()
            .reverse()
            .map((ev) => (
              <li key={ev.id} className="le-card" style={{ marginBottom: '0.4rem', padding: '0.5rem' }}>
                <strong>{ev.kind}</strong> · <span className="le-muted">{ev.ts}</span>
                <div>
                  actor: <code className="le-mono">{ev.actor ?? '—'}</code> · resource:{' '}
                  <code className="le-mono">{ev.resource}</code>
                  {ev.project_slug ? (
                    <>
                      {' '}
                      · project: <code className="le-mono">{ev.project_slug}</code>
                    </>
                  ) : null}
                </div>
                {ev.detail && Object.keys(ev.detail).length > 0 ? (
                  <TechnicalDetails summary="Event payload (inspect)">
                    <pre className="le-preview le-json" style={{ fontSize: '0.75rem', margin: 0 }}>
                      {JSON.stringify(ev.detail, null, 2)}
                    </pre>
                  </TechnicalDetails>
                ) : null}
              </li>
            ))}
        </ul>
      ) : null}
    </>
  )
}
