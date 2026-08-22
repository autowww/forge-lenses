import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, apiGetJson } from '../api/http'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'
import { AdvancedSurfaceFraming, PageHeader, StatePanel, TechnicalDetails } from '../components/page'
import { resolveUxFailure, type UxResolvedFailure } from '../lib/uxPageState'
import {
  ADMIN_INSPECT_COPY,
  ADVANCED_SURFACE_FRAMES,
  ROUTE_SUBTITLE,
  STUDIO_VOCAB,
} from '../nav/studioVisibleCopy'

type HealthRow = {
  id?: string
  label?: string
  enabled?: boolean
  healthy?: boolean
  provider_kind?: string
  hints?: string[]
}

type HealthRes = {
  ok?: boolean
  summary?: { connector_count?: number; healthy_count?: number; degraded_count?: number }
  connectors?: HealthRow[]
}

type AuthStatus = {
  session_login?: string | null
  workspace_super_admin?: boolean
  access_policy_enforced?: boolean
  oidc_configured?: boolean
  auth_provider?: string | null
}

export function GovernanceConnectorsPage() {
  useLensesCopilotPage({ route: 'governance-connectors', defaultQuery: ADMIN_INSPECT_COPY.copilotConnectorHealth })
  const [health, setHealth] = useState<HealthRes | null>(null)
  const [auth, setAuth] = useState<AuthStatus | null>(null)
  const [err, setErr] = useState<UxResolvedFailure | null>(null)
  const [loading, setLoading] = useState(true)
  const [retryNonce, setRetryNonce] = useState(0)

  useEffect(() => {
    let cancel = false
    setLoading(true)
    Promise.all([
      apiGetJson<HealthRes>('/api/connectors/health').catch((e) => {
        if (e instanceof ApiError && e.status === 403) {
          return { ok: false, _forbidden: true } as HealthRes & { _forbidden?: boolean }
        }
        throw e
      }),
      apiGetJson<AuthStatus>('/api/auth/status').catch(() => ({})),
    ])
      .then(([h, a]) => {
        if (cancel) return
        setHealth(h)
        setAuth(a)
        setErr(null)
      })
      .catch((e) => {
        if (!cancel) setErr(resolveUxFailure(e))
      })
      .finally(() => {
        if (!cancel) setLoading(false)
      })
    return () => {
      cancel = true
    }
  }, [retryNonce])

  const forbidden = health && (health as { _forbidden?: boolean })._forbidden

  return (
    <>
      <PageHeader
        title="Connector health"
        preface={
          <Link to="/governance/audit" className="forge-support">
            Audit log →
          </Link>
        }
        subtitle={ROUTE_SUBTITLE.connectorHealth}
      />
      <div style={{ marginTop: '-0.35rem', marginBottom: '0.75rem' }}>
        <AdvancedSurfaceFraming frame={ADVANCED_SURFACE_FRAMES.connectorHealth} />
      </div>
      <TechnicalDetails summary="Session and sign-in (inspect)">
        {auth?.session_login ? (
          <p className="forge-support" style={{ margin: 0 }}>
            Signed in as <code className="le-mono">{auth.session_login}</code>
            {auth.auth_provider ? (
              <>
                {' '}
                via <code className="le-mono">{auth.auth_provider}</code>
              </>
            ) : null}
            {auth.oidc_configured ? ' · OIDC available' : null}
            {auth.access_policy_enforced ? ' · Access policy enforced' : null}
            {auth.workspace_super_admin ? ' · Workspace super admin' : null}
          </p>
        ) : (
          <p className="forge-support" style={{ margin: 0 }}>
            Not signed in — use the account menu when RBAC is on. OIDC:{' '}
            <a href="/api/auth/oidc/login">Start SSO</a> (requires server configuration).
          </p>
        )}
      </TechnicalDetails>
      {loading ? (
        <StatePanel
          variant="loading"
          title="Loading connectors"
          description="Checking delivery integrations (CI, quality, release, ops) from your workspace."
        />
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
          title="Access denied"
          description="You need a project membership or workspace super admin to view connector health when access policy is enforced."
        />
      ) : null}
      {!loading && !err && !forbidden && health?.summary ? (
        <p className="forge-support">
          {health.summary.healthy_count ?? 0} healthy / {health.summary.connector_count ?? 0} connectors
          {health.summary.degraded_count ? ` · ${health.summary.degraded_count} degraded` : null}
        </p>
      ) : null}
      <ul className="le-list" style={{ listStyle: 'none', paddingLeft: 0 }}>
        {(health?.connectors ?? []).map((c) => (
          <li key={c.id} className="le-card" style={{ marginBottom: '0.5rem', padding: '0.65rem' }}>
            <strong>{c.label ?? c.id}</strong>{' '}
            <span className={c.healthy ? 'le-muted' : ''} style={{ color: c.healthy ? undefined : 'var(--le-risk, #c96)' }}>
              {c.healthy ? '● OK' : '● Check'}
            </span>
            <span className="forge-support" style={{ fontSize: '0.85rem', display: 'block', marginTop: '0.2rem' }}>
              {c.enabled === false ? 'Disabled · ' : null}
              {c.provider_kind ? `Provider kind: ${c.provider_kind}` : null}
            </span>
            <TechnicalDetails summary="Connector record (inspect)">
              <p className="forge-support" style={{ margin: 0, fontSize: '0.85rem' }}>
                <code className="le-mono">{c.id ?? '—'}</code> · provider: {c.provider_kind ?? '—'} · enabled:{' '}
                {c.enabled ? 'yes' : 'no'}
              </p>
            </TechnicalDetails>
            {(c.hints ?? []).length > 0 ? (
              <ul className="le-list" style={{ fontSize: '0.82rem', marginTop: '0.35rem' }}>
                {c.hints!.map((h, i) => (
                  <li key={i}>{h}</li>
                ))}
              </ul>
            ) : null}
          </li>
        ))}
      </ul>
      <p className="forge-support">
        <Link to="/">{STUDIO_VOCAB.overview}</Link>
      </p>
    </>
  )
}
