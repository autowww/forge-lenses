import { describe, expect, it } from 'vitest'
import { slugifyExportBaseName } from './studioPageExport'

describe('slugifyExportBaseName', () => {
  it('removes unsafe characters and collapses whitespace', () => {
    expect(slugifyExportBaseName('Foo / Bar')).toBe('Foo-Bar')
  })

  it('falls back when empty', () => {
    expect(slugifyExportBaseName('   ')).toBe('forge-studio-page')
  })
})
