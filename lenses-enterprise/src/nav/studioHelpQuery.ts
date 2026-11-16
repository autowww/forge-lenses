/** Deep-link query to reopen the Flow / Artifacts explainer on the workspace overview. */
export const STUDIO_HELP_QUERY = 'studioHelp' as const
export const STUDIO_HELP_LENS_VALUE = 'lens' as const

export function flowArtifactsHelpHomeTo(): string {
  return `/?${STUDIO_HELP_QUERY}=${STUDIO_HELP_LENS_VALUE}`
}
