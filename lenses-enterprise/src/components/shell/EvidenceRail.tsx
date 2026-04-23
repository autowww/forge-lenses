import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { apiGetJson } from '../../api/http'
import { useNavigationMode } from '../../nav/useNavigationMode'
import { useShellChrome } from '../../context/ShellChromeContext'
import { useWorkspace } from '../../context/WorkspaceContext'
import { TechnicalDetails } from '../page/TechnicalDetails'
import { buildContextualRailModel } from './contextualRail/buildContextualRailModel'
import type { LlmSetupDiagnosticsSlice } from './contextualRail/buildContextualRailModel'
import type { ContextualRailLink } from './contextualRail/types'

function RailLink({ item }: { item: ContextualRailLink }) {
  const cls =
    item.variant === 'primary'
      ? 'le-evidence-rail__link le-evidence-rail__link--primary'
      : 'le-evidence-rail__link'
  if (item.to) {
    return (
      <Link className={cls} to={item.to}>
        {item.label}
      </Link>
    )
  }
  return (
    <a
      className={cls}
      href={item.href}
      {...(item.external ? { target: '_blank', rel: 'noreferrer' } : {})}
    >
      {item.label}
      {item.external ? <span aria-hidden="true"> ↗</span> : null}
    </a>
  )
}

function LinkList({ items }: { items: ContextualRailLink[] }) {
  if (items.length === 0) return null
  return (
    <ul className="le-evidence-rail__list">
      {items.map((item) => (
        <li key={`${item.label}-${item.to ?? item.href ?? ''}`}>
          <RailLink item={item} />
        </li>
      ))}
    </ul>
  )
}

type LlmDiagApi = {
  ok?: boolean
  routing_mode?: string
  connected_providers?: number
  connected_provider_ids?: string[]
  next_recommended_step?: string
  cost_note?: string
}

export function EvidenceRail() {
  const { railCollapsed, setRailCollapsed } = useShellChrome()
  const { pathname, search } = useLocation()
  const { mode } = useNavigationMode()
  const workspace = useWorkspace()
  const [llmSetup, setLlmSetup] = useState<LlmSetupDiagnosticsSlice | undefined>(undefined)

  useEffect(() => {
    if (pathname !== '/settings/llm') {
      setLlmSetup(undefined)
      return
    }
    let cancelled = false
    setLlmSetup({ loading: true, data: null })
    void apiGetJson<LlmDiagApi>('/api/llm/diagnostics')
      .then((body) => {
        if (cancelled) return
        if (body?.ok === false) {
          setLlmSetup({ loading: false, error: true, data: null })
          return
        }
        setLlmSetup({
          loading: false,
          data: {
            connected_providers: Number(body.connected_providers) || 0,
            connected_provider_ids: Array.isArray(body.connected_provider_ids)
              ? body.connected_provider_ids.map(String)
              : [],
            routing_mode: String(body.routing_mode || 'single'),
            next_recommended_step: String(body.next_recommended_step || '').trim(),
            cost_note: typeof body.cost_note === 'string' ? body.cost_note : undefined,
          },
        })
      })
      .catch(() => {
        if (!cancelled) setLlmSetup({ loading: false, error: true, data: null })
      })
    return () => {
      cancelled = true
    }
  }, [pathname])

  const model = buildContextualRailModel({
    pathname,
    search: search || '',
    mode,
    workspace: {
      loading: workspace.loading,
      error: workspace.error,
      errorDescription: workspace.errorDescription,
      errorDetail: workspace.errorDetail,
      state: workspace.state,
    },
    llmSetup: pathname === '/settings/llm' ? (llmSetup ?? { loading: true, data: null }) : undefined,
  })

  return (
    <aside
      className={`le-evidence-rail${railCollapsed ? ' le-evidence-rail--collapsed' : ''}`}
      aria-label="Contextual guidance"
    >
      <div className="le-evidence-rail__toolbar">
        <h2 className="le-evidence-rail__title">{model.title}</h2>
        <button
          type="button"
          className="le-evidence-rail__collapse"
          onClick={() => setRailCollapsed(!railCollapsed)}
          aria-expanded={!railCollapsed}
        >
          {railCollapsed ? 'Show' : 'Hide'}
        </button>
      </div>
      {!railCollapsed && (
        <>
          {model.status ? (
            <div
              className={`le-evidence-rail__status le-evidence-rail__status--${model.status.tone ?? 'muted'}`}
            >
              <span className="le-evidence-rail__status-label">{model.status.label}</span>
              <span className="le-evidence-rail__status-value">{model.status.value}</span>
            </div>
          ) : null}

          {model.workspaceAlert ? (
            <div className="le-evidence-rail__callout le-evidence-rail__callout--alert">
              <div className="le-evidence-rail__callout-title">{model.workspaceAlert.title}</div>
              <p className="le-evidence-rail__callout-body">{model.workspaceAlert.body}</p>
              {model.workspaceAlert.technicalDetail ? (
                <details className="le-evidence-rail__technical">
                  <summary>Show technical details</summary>
                  <pre className="le-evidence-rail__technical-pre">{model.workspaceAlert.technicalDetail}</pre>
                </details>
              ) : null}
              {model.workspaceAlert.showWorkspaceRetry ? (
                <button
                  type="button"
                  className="le-evidence-rail__retry le-btn le-btn--primary"
                  onClick={() => void workspace.refresh()}
                >
                  Retry workspace scan
                </button>
              ) : null}
              <LinkList items={model.workspaceAlert.actions} />
            </div>
          ) : null}

          {model.recovery ? (
            <div className="le-evidence-rail__callout le-evidence-rail__callout--recovery">
              <div className="le-evidence-rail__callout-title">{model.recovery.title}</div>
              <p className="le-evidence-rail__callout-body">{model.recovery.body}</p>
              <LinkList items={model.recovery.actions} />
            </div>
          ) : null}

          {model.showLead === false ? null : <p className="le-evidence-rail__lead">{model.lead}</p>}

          {model.actions.length > 0 ? (
            <>
              <div className="le-evidence-rail__section-label">Next steps</div>
              <LinkList items={model.actions} />
            </>
          ) : null}

          {model.related && model.related.length > 0 ? (
            <details className="le-evidence-rail__related-wrap">
              <summary className="le-evidence-rail__related-summary">More links</summary>
              <LinkList items={model.related} />
            </details>
          ) : null}

          {model.devLink ? (
            <TechnicalDetails summary="Developer / raw data" className="le-evidence-rail__dev-wrap">
              <p className="le-evidence-rail__dev">
                <a href={model.devLink.href} className="le-evidence-rail__dev-link">
                  {model.devLink.label}
                </a>
              </p>
            </TechnicalDetails>
          ) : null}
        </>
      )}
    </aside>
  )
}
