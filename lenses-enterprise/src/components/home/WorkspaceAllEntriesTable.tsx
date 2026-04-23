import { Link } from 'react-router-dom'
import type { WorkspaceChild } from '../../api/workspace'

type Props = {
  sorted: WorkspaceChild[]
}

export function WorkspaceAllEntriesTable({ sorted }: Props) {
  return (
    <div className="le-table-wrap">
      <table className="le-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Path</th>
            <th>Kind</th>
            <th>Branch</th>
            <th>HEAD</th>
            <th>Standards</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((ch) => (
            <tr
              key={ch.name}
              className={
                ch.name === '__pycache__' || ch.name === 'node_modules' ? 'le-row--dim' : undefined
              }
            >
              <td className="le-name">
                <Link to={`/projects/${encodeURIComponent(ch.name)}`}>{ch.name}</Link>
              </td>
              <td className="le-mono">{ch.path ?? '—'}</td>
              <td>
                <span className={`le-badge${ch.is_git ? ' le-badge--git' : ''}`}>
                  {ch.is_git ? 'Repo' : 'Folder'}
                </span>
                {ch.is_git && ch.git && (ch.git as { dirty?: boolean }).dirty && (
                  <>
                    {' '}
                    <span className="le-badge le-badge--dirty">Dirty</span>
                  </>
                )}
              </td>
              <td className="le-mono">
                {ch.is_git && ch.git && String((ch.git as { branch?: string }).branch || '').trim()
                  ? String((ch.git as { branch?: string }).branch)
                  : '—'}
              </td>
              <td className="le-mono">
                {ch.is_git &&
                ch.git &&
                String((ch.git as { head_short?: string }).head_short || '').trim()
                  ? String((ch.git as { head_short?: string }).head_short)
                  : '—'}
              </td>
              <td>
                {ch.standards_compliance && typeof ch.standards_compliance.score === 'number' ? (
                  <>
                    <span
                      className={
                        'le-tier ' +
                        (ch.standards_compliance.tier === 'good'
                          ? 'le-tier--good'
                          : ch.standards_compliance.tier === 'partial'
                            ? 'le-tier--partial'
                            : 'le-tier--minimal')
                      }
                    >
                      {ch.standards_compliance.score}/100
                    </span>{' '}
                    <span className="le-muted" style={{ fontSize: '0.7rem' }}>
                      {ch.standards_compliance.tier}
                    </span>
                  </>
                ) : (
                  '—'
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
