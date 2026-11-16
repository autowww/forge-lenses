/**
 * Sprint UX0 — canonical surface states for Studio pages.
 * Maps technical failures to user-facing copy + optional technical payload for disclosure.
 */

import { classifyFetchError, type ClassifiedFetchFailure } from './classifyFetchError'

/** Logical UX state for shells, panels, and recovery flows (not 1:1 with StatePanel CSS variants). */
export type UxSurfaceKind =
  | 'loading'
  | 'empty'
  | 'missing_configuration'
  | 'permission_denied'
  | 'unavailable'
  | 'degraded'
  | 'beta'
  | 'readonly'
  | 'disconnected'
  | 'invalid'

export type UxResolvedFailure = {
  kind: UxSurfaceKind
  /** Primary line for titles / banners */
  title: string
  /** Supporting copy */
  description: string
  /** Collapsible diagnostics (HTTP body, paths, codes) */
  technical: string | null
  /** Underlying classifier bucket (telemetry / logic) */
  fetchKind: ClassifiedFetchFailure['kind']
}

const COPILOT_PREFILL_PARAM = 'prefill'

/** Build `/studio/chat?prefill=…` href for recovery prompts (basename is /studio). */
export function chatRecoveryHref(prompt: string): string {
  const q = new URLSearchParams()
  q.set(COPILOT_PREFILL_PARAM, prompt)
  return `/chat?${q.toString()}`
}

/**
 * Turn any thrown value into a structured UX failure (never exposes raw HTTP as the title).
 */
export function resolveUxFailure(err: unknown): UxResolvedFailure {
  const c = classifyFetchError(err)
  return classifiedFailureToUx(c)
}

export function classifiedFailureToUx(c: ClassifiedFetchFailure): UxResolvedFailure {
  const technicalParts = [c.detail, c.httpStatus != null ? `Response status: ${c.httpStatus}` : null].filter(
    (x): x is string => Boolean(x && String(x).trim()),
  )
  const technical = technicalParts.length ? technicalParts.join('\n') : null

  switch (c.kind) {
    case 'permission':
      return {
        kind: 'permission_denied',
        title: 'Permission required',
        description: c.summary,
        technical,
        fetchKind: c.kind,
      }
    case 'not_found':
      return {
        kind: 'missing_configuration',
        title: 'Nothing here yet',
        description: c.summary,
        technical,
        fetchKind: c.kind,
      }
    case 'network':
      return {
        kind: 'disconnected',
        title: 'This data source is unavailable right now',
        description:
          'We could not load data from your workspace service. Confirm the Lenses app is running and you opened Studio from a supported URL, then try again.',
        technical: technical ?? c.detail ?? null,
        fetchKind: c.kind,
      }
    case 'server':
      return {
        kind: 'unavailable',
        title: 'This data source is unavailable right now',
        description: c.summary,
        technical,
        fetchKind: c.kind,
      }
    case 'scan':
      return {
        kind: 'degraded',
        title: 'Workspace data is incomplete',
        description: c.summary,
        technical,
        fetchKind: c.kind,
      }
    default:
      return {
        kind: 'unavailable',
        title: 'Something went wrong',
        description: c.summary,
        technical,
        fetchKind: c.kind,
      }
  }
}

export type AssistShortcutSpec = { context: string; detail?: string }

/** Default Copilot deep-links for empty, error, and setup states (task-first prompts). */
export function assistShortcutsForContext(spec: AssistShortcutSpec): { prompt: string; label: string }[] {
  const { context, detail } = spec
  const d = detail?.trim()
  const tail = d ? ` ${d}` : ''
  return [
    {
      label: 'Explain this state',
      prompt: `I'm on "${context}" in Forge Lenses Studio.${tail} Explain what this screen is for and what the current state means in plain language.`,
    },
    {
      label: 'What can I do next?',
      prompt: `I'm on "${context}" in Forge Lenses Studio.${tail} What is the single best next step for me?`,
    },
    {
      label: 'Help me recover setup',
      prompt: `Help me recover Forge Lenses setup for "${context}".${tail} Cover workspace scan, local server, and where to find Admin & inspect / AI Setup without assuming I know internal paths.`,
    },
    {
      label: 'Summarize what is missing',
      prompt: `Summarize what is missing or blocked on "${context}" in Lenses based on what a user would see when data or connectors are incomplete.${tail}`,
    },
  ]
}

/** Workspace bootstrap: invalid JSON envelope from /api/workspace-state. */
export function workspaceInvalidEnvelopeUx(): UxResolvedFailure {
  return {
    kind: 'degraded',
    title: 'Workspace snapshot was incomplete',
    description:
      'Lenses responded, but the workspace data was not in the expected shape. Try reloading after the server finishes scanning.',
    technical: 'Workspace scan returned an empty or invalid response.',
    fetchKind: 'unknown',
  }
}
