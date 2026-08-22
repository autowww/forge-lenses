import { describe, expect, it } from 'vitest'
import {
  clusterByRepoHint,
  filterRoadmapsForRepoHint,
  repoHintForWbsPath,
  roadmapLocationLabel,
  wbsBacklogPickerLabel,
} from './planScopeCluster'

describe('clusterByRepoHint', () => {
  it('groups by repo_hint', () => {
    const g = clusterByRepoHint([
      { rel_path: 'a/x.md', repo_hint: 'Situ8' },
      { rel_path: 'a/y.md', repo_hint: 'Situ8' },
      { rel_path: 'b/z.md', repo_hint: 'blueprints' },
    ])
    expect(g).toHaveLength(2)
    expect(g.find((c) => c.repoHint === 'Situ8')?.items).toHaveLength(2)
  })
})

describe('filterRoadmapsForRepoHint', () => {
  it('filters by repo_hint', () => {
    const r = filterRoadmapsForRepoHint(
      [
        { rel_path: 'Situ8/docs/ROADMAP.md', repo_hint: 'Situ8' },
        { rel_path: 'blueprints/docs/ROADMAP.md', repo_hint: 'blueprints' },
      ],
      'Situ8',
    )
    expect(r).toHaveLength(1)
    expect(r[0]?.rel_path).toContain('Situ8')
  })
})

describe('repoHintForWbsPath', () => {
  it('returns hint for path', () => {
    expect(
      repoHintForWbsPath([{ rel_path: 'Situ8/docs/requirements/WBS.md', repo_hint: 'Situ8' }], 'Situ8/docs/requirements/WBS.md'),
    ).toBe('Situ8')
  })
})

describe('roadmapLocationLabel', () => {
  it('strips repo prefix and roadmap filename', () => {
    expect(roadmapLocationLabel('Situ8/docs/ROADMAP.md', 'Situ8')).toBe('docs')
  })
})

describe('wbsBacklogPickerLabel', () => {
  it('drops repo prefix, extension, and generic WBS filename for a human path', () => {
    expect(wbsBacklogPickerLabel('blueprints/docs/requirements/WBS.md', 'blueprints')).toBe('Docs › Requirements')
    expect(wbsBacklogPickerLabel('x/WBS.md', '')).toBe('X')
  })

  it('returns Backlog when nothing remains after stripping', () => {
    expect(wbsBacklogPickerLabel('repo/WBS.md', 'repo')).toBe('Backlog')
  })
})
