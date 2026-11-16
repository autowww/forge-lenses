import { useEffect, useMemo, useState } from 'react'
import type { DocsHealthCluster, DocsHealthFinding, DocsHealthSessionEvent, DocsHealthSessionPayload } from '../../api/docsHealth'
import { ForgeReviewPanel } from '../../forgesdlc-kitchensink'
import { proposedKindToArtifactTab } from '../../lib/docsHealthStageFlow'
import { DocsHealthChangesReviewSummary } from './DocsHealthChangesReviewSummary'

export type DraftArtifactTabId = 'patch' | 'diagram' | 'adr'

export type DocsDraftArtifactsTabsProps = {
  session: DocsHealthSessionPayload | null
  /** Controlled artifact subtab. */
  activeArtifactTab?: DraftArtifactTabId
  onArtifactTabChange?: (tab: DraftArtifactTabId) => void
  /** For review summary risk / scope. */
  cluster?: Pick<DocsHealthCluster, 'primary_severity'> | null
  finding?: DocsHealthFinding | null
  /** Awaiting human approval — show review summary + link to pinned actions. */
  awaitingApproval?: boolean
}

const TAB_LABELS: Record<DraftArtifactTabId, string> = {
  patch: 'Markdown changes',
  diagram: 'Architecture diagram',
  adr: 'Decision record',
}

const PANEL_TITLES: Record<DraftArtifactTabId, string> = {
  patch: 'Draft documentation changes',
  diagram: 'Draft architecture diagram',
  adr: 'Draft decision record',
}

/**
 * Changes: artifact subtabs for documentation, diagram, and decision record (under Draft changes workflow stage).
 */
export function DocsDraftArtifactsTabs({
  session,
  activeArtifactTab: controlledTab,
  onArtifactTabChange,
  cluster,
  finding,
  awaitingApproval = false,
}: DocsDraftArtifactsTabsProps) {
  const [internalTab, setInternalTab] = useState<DraftArtifactTabId>('patch')
  const isControlled = controlledTab !== undefined
  const tab = isControlled ? controlledTab : internalTab

  const setTab = (next: DraftArtifactTabId) => {
    if (isControlled) onArtifactTabChange?.(next)
    else setInternalTab(next)
  }

  useEffect(() => {
    if (isControlled) return
    setInternalTab(proposedKindToArtifactTab(session?.proposed_patch_kind))
  }, [session?.proposed_patch_kind, session?.id, isControlled])

  const patchText = session?.proposed_patch?.content
  const patchPath = session?.proposed_patch?.path

  const diagramEvent = useMemo(
    () => session?.events?.find((e) => e.type === 'diff' && String(e.path || '').match(/\.(svg|png|md)$/i)),
    [session?.events],
  )

  const adrEvent = useMemo(() => {
    const evs = session?.events ?? []
    return evs.find((e) => e.type === 'file_change' && String(e.path || '').match(/adr|decisions/i)) as
      | DocsHealthSessionEvent
      | undefined
  }, [session?.events])

  const hasPatch = Boolean(patchText || patchPath)
  const hasDiagram = Boolean(diagramEvent?.unified || diagramEvent?.path)
  const hasAdr = Boolean(adrEvent?.path || adrEvent?.body)

  const tabIds = ['patch', 'diagram', 'adr'] as const

  return (
    <section id="docs-health-drafts-anchor" className="le-dh-changes" aria-label="Changes">
      <h3 className="le-dh-wf-panel__h">Changes</h3>
      <p className="forge-support le-dh-changes__lead">
        Proposed updates grouped for review. Approval stays on the pinned action bar so decisions stay explicit.
      </p>

      <DocsHealthChangesReviewSummary
        session={session}
        cluster={cluster}
        finding={finding}
        showApprovalHint={awaitingApproval}
      />

      <div className="le-dh-changes__tabs-wrap">
        <p className="le-dh-changes__tabs-label" id="dh-changes-tabs-label">
          Artifact type
        </p>
        <ul className="le-dh-draft-tabs__list" role="tablist" aria-labelledby="dh-changes-tabs-label">
          {tabIds.map((id) => (
            <li key={id} role="presentation">
              <button
                type="button"
                role="tab"
                aria-selected={tab === id}
                className={`le-dh-draft-tabs__tab ${tab === id ? 'le-dh-draft-tabs__tab--active' : ''}`}
                onClick={() => setTab(id)}
              >
                {TAB_LABELS[id]}
              </button>
            </li>
          ))}
        </ul>
      </div>

      <div role="tabpanel" className="le-dh-draft-tabs__panel" aria-live="polite">
        {tab === 'patch' ? (
          hasPatch ? (
            <ForgeReviewPanel title={PANEL_TITLES.patch} kicker={patchPath ? <code>{patchPath}</code> : null}>
              <pre
                className="le-preview le-dh-changes__diff"
                style={{ fontSize: '0.8rem', whiteSpace: 'pre-wrap', maxHeight: '24rem', overflow: 'auto' }}
              >
                {patchText || '—'}
              </pre>
            </ForgeReviewPanel>
          ) : (
            <ForgeReviewPanel title={PANEL_TITLES.patch}>
              <p className="le-dh-changes__empty">No draft documentation changes were generated for this run.</p>
            </ForgeReviewPanel>
          )
        ) : null}

        {tab === 'diagram' ? (
          hasDiagram ? (
            <ForgeReviewPanel title={PANEL_TITLES.diagram} kicker={diagramEvent?.path ? <code>{diagramEvent.path}</code> : null}>
              <p className="le-dh-changes__diagram-body">{diagramEvent?.unified || 'See Run activity for full output.'}</p>
            </ForgeReviewPanel>
          ) : (
            <ForgeReviewPanel title={PANEL_TITLES.diagram}>
              <p className="le-dh-changes__empty">No draft architecture diagram was generated for this run.</p>
            </ForgeReviewPanel>
          )
        ) : null}

        {tab === 'adr' ? (
          hasAdr ? (
            <ForgeReviewPanel title={PANEL_TITLES.adr} kicker={adrEvent?.path ? <code>{adrEvent.path}</code> : null}>
              <p className="forge-support">{adrEvent?.body || adrEvent?.summary || 'Recorded in session timeline.'}</p>
            </ForgeReviewPanel>
          ) : (
            <ForgeReviewPanel title={PANEL_TITLES.adr}>
              <p className="le-dh-changes__empty">No draft decision record was generated for this run.</p>
            </ForgeReviewPanel>
          )
        ) : null}
      </div>
    </section>
  )
}
