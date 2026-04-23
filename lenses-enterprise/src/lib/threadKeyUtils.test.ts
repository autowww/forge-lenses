import { describe, expect, it } from 'vitest'
import { splitThreadKey } from './threadKeyUtils'

describe('splitThreadKey', () => {
  it('splits pathname and search', () => {
    expect(splitThreadKey('/projects/acme?tab=docs')).toEqual({
      pathname: '/projects/acme',
      search: '?tab=docs',
    })
  })
  it('handles no query', () => {
    expect(splitThreadKey('/search')).toEqual({ pathname: '/search', search: '' })
  })
})
