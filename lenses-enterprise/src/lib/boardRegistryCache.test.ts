import { afterEach, describe, expect, it } from 'vitest'
import { clearBoardRegistryCache, readBoardRegistryCache, writeBoardRegistryCache } from './boardRegistryCache'

const WS = '/tmp/forge-studio-test-ws'

describe('boardRegistryCache', () => {
  afterEach(() => {
    clearBoardRegistryCache(WS)
  })

  it('roundtrips payload scoped to workspace root', () => {
    const payload = {
      version: 1,
      projects: { myrepo: [{ id: 'abc', label: 'L', storage: 'local' as const }] },
    }
    writeBoardRegistryCache(WS, payload, '2026-01-02T03:04:05.000Z')
    const got = readBoardRegistryCache(WS)
    expect(got?.savedAtIso).toBe('2026-01-02T03:04:05.000Z')
    expect(got?.payload.projects?.myrepo).toHaveLength(1)
    expect(got?.payload.projects?.myrepo?.[0]?.id).toBe('abc')
    expect(readBoardRegistryCache('/other/ws')).toBeNull()
  })

  it('returns null when empty', () => {
    clearBoardRegistryCache(WS)
    expect(readBoardRegistryCache(WS)).toBeNull()
  })
})
