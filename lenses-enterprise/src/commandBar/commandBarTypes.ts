export type CommandMode = 'find' | 'ask' | 'do'

export type FindResultKind = 'nav' | 'search_hit' | 'suggestion'

export type FindResult = {
  id: string
  kind: FindResultKind
  label: string
  description?: string
  /** In-app route — Find navigates here. */
  to?: string
  href?: string
  external?: boolean
  /**
   * When set (typically with kind `suggestion`), choosing this row switches the command bar to Ask
   * with this query instead of navigating away — keeps Ask in the primary command flow.
   */
  askPrefill?: string
}

export type DoActionKind = 'navigate' | 'copy_draft' | 'open_advanced'

export type DoAction = {
  id: string
  label: string
  description?: string
  kind: DoActionKind
  /** For navigate */
  to?: string
  /** For copy_draft — preview only until user copies */
  draftTitle?: string
  draftBody?: string
}
