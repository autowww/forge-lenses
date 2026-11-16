import { describe, expect, it } from 'vitest'
import {
  bucketRecentSessions,
  bucketSessionStatus,
  bucketTaskletRuns,
  bucketTaskletState,
  pickLatestSessionModel,
  sumSessionTokens,
} from './docsHealthProjectRunBuckets'

describe('bucketTaskletState', () => {
  it('queues created and preparing', () => {
    expect(bucketTaskletState('created')).toBe('queue')
    expect(bucketTaskletState('preparing')).toBe('queue')
  })
  it('runs active states', () => {
    expect(bucketTaskletState('running')).toBe('running')
    expect(bucketTaskletState('awaiting_input')).toBe('running')
    expect(bucketTaskletState('verifying')).toBe('running')
    expect(bucketTaskletState('paused')).toBe('running')
    expect(bucketTaskletState('stopping')).toBe('running')
  })
  it('terminates completed vs failed', () => {
    expect(bucketTaskletState('completed')).toBe('completed')
    expect(bucketTaskletState('failed')).toBe('failed')
    expect(bucketTaskletState('stopped')).toBe('failed')
  })
})

describe('bucketTaskletRuns', () => {
  it('splits rows into four arrays', () => {
    const rows = [
      { id: '1', state: 'created' },
      { id: '2', state: 'running' },
      { id: '3', state: 'completed' },
      { id: '4', state: 'failed' },
    ]
    const b = bucketTaskletRuns(rows)
    expect(b.queue.map((r) => r.id)).toEqual(['1'])
    expect(b.running.map((r) => r.id)).toEqual(['2'])
    expect(b.completed.map((r) => r.id)).toEqual(['3'])
    expect(b.failed.map((r) => r.id)).toEqual(['4'])
  })
})

describe('bucketSessionStatus', () => {
  it('maps terminal session statuses', () => {
    expect(bucketSessionStatus('completed')).toBe('completed')
    expect(bucketSessionStatus('failed')).toBe('failed')
    expect(bucketSessionStatus('cancelled')).toBe('failed')
  })
  it('treats in-flight as running', () => {
    expect(bucketSessionStatus('running')).toBe('running')
    expect(bucketSessionStatus('awaiting_input')).toBe('running')
    expect(bucketSessionStatus('paused')).toBe('running')
  })
})

describe('bucketRecentSessions', () => {
  it('partitions sessions', () => {
    const s = bucketRecentSessions([
      { session_id: 'a', status: 'completed' },
      { session_id: 'b', status: 'failed' },
      { session_id: 'c', status: 'running' },
    ])
    expect(s.completed.map((x) => x.session_id)).toEqual(['a'])
    expect(s.failed.map((x) => x.session_id)).toEqual(['b'])
    expect(s.running.map((x) => x.session_id)).toEqual(['c'])
  })
})

describe('sumSessionTokens', () => {
  it('sums positive totals', () => {
    expect(sumSessionTokens([{ total_tokens: 100 }, { total_tokens: 50 }])).toBe(150)
  })
  it('ignores missing or zero', () => {
    expect(sumSessionTokens([{ total_tokens: 0 }, {}])).toBe(0)
  })
})

describe('pickLatestSessionModel', () => {
  it('returns last_model from newest by updated_at', () => {
    const m = pickLatestSessionModel([
      { session_id: 'old', updated_at: '2020-01-01T00:00:00Z', last_model: 'a' },
      { session_id: 'new', updated_at: '2025-01-01T00:00:00Z', last_model: 'b' },
    ])
    expect(m).toBe('b')
  })
})
