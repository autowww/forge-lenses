import { useCallback, useState } from 'react'
import { apiPostJson } from '../../api/http'
import { MarkdownBody } from '../MarkdownBody'

type SizeGate = {
  has_proposal?: boolean
  has_spec?: boolean
  validate_strict_green?: boolean
  l4_hold?: boolean
  wiki_stale?: boolean
}

type DualWikiSide = {
  in_repo?: string
  handbook_shell?: string
  notes?: string
  fresh?: boolean
  skipped?: boolean
  reason?: string
}

type DualWiki = {
  stale?: boolean
  sides?: DualWikiSide[]
  reasons?: string[]
  refresh_allowed?: boolean
}

type Props = {
  hub: Record<string, unknown>
  epicId: string
  wbsP: string
  repo: string
  onRefreshComplete?: () => void
}

export function EpicHubPanel({ hub, epicId, wbsP, repo, onRefreshComplete }: Props) {
  const proposal = String(hub.proposal_excerpt || '')
  const spec = String(hub.spec_excerpt || '')
  const validateSummary = String(hub.validate_summary || '')
  const column = String(hub.column || '')
  const changeSlug = String(hub.change_slug || '')
  const gate = (hub.size_gate || {}) as SizeGate
  const dualWiki = (hub.dual_wiki || {}) as DualWiki
  const [refreshing, setRefreshing] = useState(false)
  const [refreshError, setRefreshError] = useState('')

  const handleRefresh = useCallback(async () => {
    setRefreshing(true)
    setRefreshError('')
    try {
      const res = await apiPostJson<Record<string, unknown>>('/api/epic-spec-board/dual-wiki-refresh', {
        epic_id: epicId,
        wbs_p: wbsP,
        repo: repo || undefined,
        change_slug: changeSlug || undefined,
      })
      if (!res.ok) {
        setRefreshError(String(res.error || res.detail || 'Refresh failed'))
        return
      }
      onRefreshComplete?.()
    } catch (e) {
      setRefreshError(e instanceof Error ? e.message : 'Refresh failed')
    } finally {
      setRefreshing(false)
    }
  }, [changeSlug, epicId, onRefreshComplete, repo, wbsP])

  const sides = dualWiki.sides ?? []

  return (
    <div className="le-epic-hub-panel le-card" style={{ padding: '1rem', marginTop: '1rem' }}>
      <header>
        <p className="le-muted" style={{ fontSize: '0.75rem', margin: 0 }}>
          Epic hub · OpenSpec
        </p>
        <h2 className="le-panel__title" style={{ marginTop: '0.25rem' }}>
          {epicId}
        </h2>
        {changeSlug ? (
          <p className="forge-support">
            Change <code className="le-mono">{changeSlug}</code>
            {column ? <> · column <strong>{column}</strong></> : null}
          </p>
        ) : (
          <p className="forge-support">No OpenSpec change yet — move from Intent to Specify on the board.</p>
        )}
      </header>

      <section style={{ marginTop: '1rem' }} aria-labelledby="le-epic-gate">
        <h3 id="le-epic-gate" className="le-panel__title" style={{ fontSize: '0.95rem' }}>
          Size gate checklist
        </h3>
        <ul className="le-list" style={{ fontSize: '0.9rem' }}>
          <li>{gate.has_proposal ? '✓' : '○'} Proposal present</li>
          <li>{gate.has_spec ? '✓' : '○'} Lite spec scenarios present</li>
          <li>{gate.validate_strict_green ? '✓' : '○'} `openspec validate --strict` green</li>
          <li>{gate.l4_hold ? '⚠ L4.2 / cross-repo hold' : '○ No L4.2 hold flagged'}</li>
          <li>{gate.wiki_stale ? '⚠' : '✓'} Local handbook HTML fresh (dual wiki)</li>
        </ul>
        <p className="forge-support">{validateSummary}</p>
      </section>

      {dualWiki.sides || dualWiki.stale !== undefined ? (
        <section style={{ marginTop: '1rem' }} aria-labelledby="le-dual-wiki">
          <h3 id="le-dual-wiki" className="le-panel__title" style={{ fontSize: '0.95rem' }}>
            Dual wiki (local derived)
          </h3>
          {sides.length ? (
            <ul className="le-list" style={{ fontSize: '0.9rem' }}>
              {sides.map((side, i) => (
                <li key={`${side.in_repo}-${i}`}>
                  {side.skipped ? (
                    <>○ <code className="le-mono">{side.in_repo || '—'}</code> — shell absent (skipped)</>
                  ) : side.fresh ? (
                    <>✓ <code className="le-mono">{side.in_repo}</code> → {side.handbook_shell}</>
                  ) : (
                    <>
                      ⚠ <code className="le-mono">{side.in_repo}</code> — {side.reason || 'stale'}
                    </>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <p className="forge-support">No handbook-bound surfaces declared on the proposal yet.</p>
          )}
          {(dualWiki.reasons?.length ?? 0) > 0 ? (
            <p className="forge-support">{dualWiki.reasons?.join(' · ')}</p>
          ) : null}
          <button
            type="button"
            className="le-btn le-btn--secondary"
            style={{ marginTop: '0.5rem' }}
            disabled={refreshing}
            onClick={() => void handleRefresh()}
          >
            {refreshing ? 'Refreshing…' : 'Refresh local handbooks'}
          </button>
          <p className="forge-support" style={{ marginTop: '0.35rem' }}>
            Rebuilds local handbook HTML only — does not publish to Firebase.
          </p>
          {refreshError ? <p className="le-error">{refreshError}</p> : null}
        </section>
      ) : null}

      {proposal ? (
        <section style={{ marginTop: '1rem' }} aria-labelledby="le-epic-proposal">
          <h3 id="le-epic-proposal" className="le-panel__title" style={{ fontSize: '0.95rem' }}>
            Proposal
          </h3>
          <MarkdownBody text={proposal} />
        </section>
      ) : null}

      {spec ? (
        <section style={{ marginTop: '1rem' }} aria-labelledby="le-epic-spec">
          <h3 id="le-epic-spec" className="le-panel__title" style={{ fontSize: '0.95rem' }}>
            Lite spec (excerpt)
          </h3>
          <MarkdownBody text={spec} />
        </section>
      ) : null}
    </div>
  )
}
