/**
 * Pluggable context snippet providers (mock for v1 — swap for real ingestion later).
 */

export type ContextSnippetKind = 'repo' | 'docs' | 'tickets'

export interface ContextSnippetProvider {
  getSnippet(kind: ContextSnippetKind, ref?: string): Promise<string>
}

export class MockContextSnippetProvider implements ContextSnippetProvider {
  async getSnippet(kind: ContextSnippetKind, ref?: string): Promise<string> {
    const r = ref?.trim() || '(no ref)'
    return `[mock ${kind}] ${r} — replace with a real provider when ingestion is wired.`
  }
}
