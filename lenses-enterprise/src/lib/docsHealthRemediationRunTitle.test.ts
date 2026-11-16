import { describe, expect, it } from 'vitest'
import { deriveShortRemediationRunTitle } from './docsHealthRemediationRunTitle'

describe('deriveShortRemediationRunTitle', () => {
  it('parses four-part canonical display name', () => {
    expect(
      deriveShortRemediationRunTitle({
        displayName: 'Docs remediation · my-proj · Minor · diagram',
      }),
    ).toBe('Diagram remediation')
  })

  it('falls back to category', () => {
    expect(deriveShortRemediationRunTitle({ category: 'ticket_ref' })).toBe('Ticket Ref remediation')
  })

  it('falls back to default label', () => {
    expect(deriveShortRemediationRunTitle({})).toBe('Documentation remediation run')
  })
})
