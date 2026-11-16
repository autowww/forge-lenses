import type { DocsHealthSessionHeaderStats } from '../../api/docsHealth'

/**
 * Planned model routing (dispatch preview) — diagnostics context, not primary run narrative.
 */
export function DocsHealthPlannedModelsTable({ header }: { header?: DocsHealthSessionHeaderStats }) {
  if (!header?.model_routing_preview?.slots) return null
  return (
    <div className="le-dh-session-routing" aria-label="Planned model routing by role">
      <h3 className="le-dh-session-routing__title">Planned model routing</h3>
      <p className="le-muted" style={{ fontSize: '0.82rem', marginTop: 0, maxWidth: '48rem' }}>
        Order follows your AI Setup model map per role. Change models under Settings → AI Setup.
      </p>
      <table className="le-dh-session-routing__table">
        <thead>
          <tr>
            <th scope="col">Role</th>
            <th scope="col">First provider</th>
            <th scope="col">Model id (settings)</th>
            <th scope="col">Fallback chain</th>
          </tr>
        </thead>
        <tbody>
          {(['triage.small', 'writer.medium', 'reviewer.high'] as const).map((key) => {
            const slot = header.model_routing_preview?.slots?.[key]
            if (!slot) return null
            const chain = (slot.chain_with_models || [])
              .map((c) => `${c.provider ?? '?'}:${c.model ?? '—'}`)
              .join(' → ')
            return (
              <tr key={key}>
                <td>{slot.label ?? key}</td>
                <td>{slot.primary_provider ?? '—'}</td>
                <td>
                  <code className="le-mono">{slot.primary_model ?? '—'}</code>
                </td>
                <td className="le-dh-session-routing__chain" title={chain}>
                  {chain || '—'}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
