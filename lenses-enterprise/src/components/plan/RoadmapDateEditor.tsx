import { useCallback, useState } from 'react'
import { apiPostJson } from '../../api/http'

export type RoadmapDateRow = {
  label: string
  epic_id: string
  initial_start: string | null
  initial_end: string | null
  target_start: string | null
  target_end: string | null
}

type RoadmapDateEditorProps = {
  relPath: string
  rows: RoadmapDateRow[]
  onSaved?: () => void
}

type DateField = 'initial_start' | 'initial_end' | 'target_start' | 'target_end'

function fieldValue(row: RoadmapDateRow, field: DateField): string {
  const v = row[field]
  return v == null ? '' : String(v)
}

export function RoadmapDateEditor({ relPath, rows, onSaved }: RoadmapDateEditorProps) {
  const [draft, setDraft] = useState<RoadmapDateRow[]>(rows)
  const [status, setStatus] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const updateCell = useCallback((index: number, field: DateField, value: string) => {
    setDraft((prev) =>
      prev.map((row, i) => (i === index ? { ...row, [field]: value || null } : row)),
    )
  }, [])

  async function save() {
    if (!relPath.trim()) return
    setSaving(true)
    setStatus('Saving…')
    try {
      const updates = draft.map((row) => ({
        epic_id: row.epic_id,
        initial_start: fieldValue(row, 'initial_start'),
        initial_end: fieldValue(row, 'initial_end'),
        target_start: fieldValue(row, 'target_start'),
        target_end: fieldValue(row, 'target_end'),
      }))
      const res = await apiPostJson<{ ok?: boolean; error?: string }>('/api/roadmap-dates', {
        rel_path: relPath,
        updates,
      })
      if (res.ok) {
        setStatus('Saved. Reload timeline charts to refresh visuals.')
        onSaved?.()
      } else {
        setStatus(res.error || 'Save failed')
      }
    } catch (e) {
      setStatus(e instanceof Error ? e.message : 'Network error')
    } finally {
      setSaving(false)
    }
  }

  if (!rows.length) {
    return (
      <p className="forge-support">
        No Initial/Target date rows found in this roadmap. Add ISO date columns per the roadmap template to enable
        editing.
      </p>
    )
  }

  return (
    <section className="le-panel le-roadmap-date-editor" aria-label="Roadmap date editor">
      <h2 className="le-plan-section__title">Epic dates</h2>
      <p className="forge-support le-plan-section__lead">
        Edit Initial and Target start/end dates. Changes are saved to the roadmap file in your workspace.
      </p>
      <div className="le-table-scroll">
        <table className="le-table">
          <thead>
            <tr>
              <th scope="col">Epic</th>
              <th scope="col">Initial start</th>
              <th scope="col">Initial end</th>
              <th scope="col">Target start</th>
              <th scope="col">Target end</th>
            </tr>
          </thead>
          <tbody>
            {draft.map((row, index) => (
              <tr key={row.epic_id || row.label || index}>
                <th scope="row">{row.label || row.epic_id || `Row ${index + 1}`}</th>
                {(['initial_start', 'initial_end', 'target_start', 'target_end'] as DateField[]).map((field) => (
                  <td key={field}>
                    <input
                      className="le-input le-mono"
                      type="date"
                      value={fieldValue(row, field)}
                      onChange={(e) => updateCell(index, field, e.target.value)}
                    />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="le-form-row" style={{ marginTop: '0.75rem' }}>
        <button type="button" className="le-btn le-btn--primary" disabled={saving} onClick={() => void save()}>
          Save dates
        </button>
        {status ? <span className="forge-support">{status}</span> : null}
      </div>
    </section>
  )
}
