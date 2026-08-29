import { useCallback, useEffect, useState } from 'react'
import { apiGetJson } from '../../api/http'

type HealthRollup = {
  ok?: boolean
  status?: string
  summary?: string
  environments?: Array<{
    ok?: boolean
    url?: string
    status?: string
    summary?: string
    checks?: Array<{ id?: string; status?: string; detail?: string }>
    envelope?: { environment?: { id?: string } }
  }>
}

type Props = {
  healthUrls: string[]
  bearer?: string
}

export function EnvironmentHealthPanel({ healthUrls, bearer = '' }: Props) {
  const [rollup, setRollup] = useState<HealthRollup | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!healthUrls.length) {
      setRollup(null)
      return
    }
    try {
      const qs = new URLSearchParams()
      for (const url of healthUrls) qs.append('url', url)
      if (bearer) qs.set('bearer', bearer)
      const out = await apiGetJson<HealthRollup>(`/api/deploy/environment-health?${qs.toString()}`)
      setRollup(out)
      setError(null)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Health probe failed')
    }
  }, [healthUrls, bearer])

  useEffect(() => {
    void load()
    const id = window.setInterval(() => void load(), 30_000)
    return () => window.clearInterval(id)
  }, [load])

  if (!healthUrls.length) return null

  return (
    <section style={{ marginTop: '1.5rem' }}>
      <div className="ks-toolbar" style={{ marginBottom: '0.5rem' }}>
        <h2 style={{ margin: 0 }}>Environment health</h2>
        <button type="button" className="ks-btn" onClick={() => void load()}>
          Refresh
        </button>
      </div>
      {error ? <p className="ks-error">{error}</p> : null}
      {rollup ? (
        <>
          <p>
            <strong>{rollup.status ?? 'unknown'}</strong>
            {rollup.summary ? ` — ${rollup.summary}` : null}
          </p>
          <table className="ks-table">
            <thead>
              <tr>
                <th>Environment</th>
                <th>Status</th>
                <th>Checks</th>
              </tr>
            </thead>
            <tbody>
              {(rollup.environments ?? []).map((row) => {
                const envId = row.envelope?.environment?.id ?? row.url ?? '—'
                const failing = (row.checks ?? []).filter((c) => c.status && c.status !== 'ok')
                return (
                  <tr key={String(envId)}>
                    <td>
                      <code>{envId}</code>
                    </td>
                    <td>{row.status ?? (row.ok ? 'ok' : 'down')}</td>
                    <td>
                      {failing.length
                        ? failing.map((c) => `${c.id}: ${c.status}`).join('; ')
                        : 'all ok'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </>
      ) : null}
    </section>
  )
}
