/**
 * Step 5 — Target & Output Pack. `session.payload.targetOutputPack` → `wizard_domain.target_stage` + `artifact_packs`.
 * Experimental Blueprints Wizard only.
 */

import type { ArtifactPackJson, OutputPackKind, TargetStage, WizardDomainJson } from './wizardDomainTypes'
import { OUTPUT_PACK_KINDS, TARGET_STAGES } from './wizardDomainTypes'

export const TARGET_PACK_LABEL_MAX = 500
export const TARGET_ARTIFACT_LINES_MAX = 12000

function isTargetStage(v: unknown): v is TargetStage {
  return typeof v === 'string' && (TARGET_STAGES as readonly string[]).includes(v)
}

function isOutputPackKind(v: unknown): v is OutputPackKind {
  return typeof v === 'string' && (OUTPUT_PACK_KINDS as readonly string[]).includes(v)
}

/** Forge label + plain-language helper (UI + a11y). */
export const TARGET_STAGE_UI: Record<
  TargetStage,
  { forgeLabel: string; plain: string }
> = {
  idea: { forgeLabel: 'Idea', plain: 'Capture intent, options, and early constraints.' },
  roadmap: { forgeLabel: 'Roadmap', plain: 'Sequence outcomes and dependencies over time.' },
  milestones: { forgeLabel: 'Milestones', plain: 'Named checkpoints with acceptance signals.' },
  wbes: { forgeLabel: 'WBEs', plain: 'Work breakdown elements — decomposed units of work.' },
  ore: { forgeLabel: 'Ore', plain: 'Raw material inputs before refinement.' },
  ingots: { forgeLabel: 'Ingots', plain: 'Refined, reusable building blocks.' },
  sparks: { forgeLabel: 'Sparks', plain: 'Small, actionable experiments or tasks.' },
  charges: { forgeLabel: 'Charges', plain: 'Committed execution units with energy and ownership.' },
}

export const OUTPUT_PACK_KIND_UI: Record<
  OutputPackKind,
  { forgeLabel: string; plain: string; defaultPackLabel: string }
> = {
  foundation_pack: {
    forgeLabel: 'Foundation Pack',
    plain: 'Mission, context, and baseline assumptions.',
    defaultPackLabel: 'Foundation Pack',
  },
  strategy_pack: {
    forgeLabel: 'Strategy Pack',
    plain: 'Goals, bets, and tradeoffs.',
    defaultPackLabel: 'Strategy Pack',
  },
  planning_pack: {
    forgeLabel: 'Planning Pack',
    plain: 'Milestones, WBEs, and dependencies.',
    defaultPackLabel: 'Planning Pack',
  },
  engineering_pack: {
    forgeLabel: 'Engineering Pack',
    plain: 'Design, interfaces, and technical notes.',
    defaultPackLabel: 'Engineering Pack',
  },
  execution_pack: {
    forgeLabel: 'Execution Pack',
    plain: 'Run plans, checklists, and delivery evidence.',
    defaultPackLabel: 'Execution Pack',
  },
}

export function defaultPackLabelForKind(kind: OutputPackKind): string {
  return OUTPUT_PACK_KIND_UI[kind]?.defaultPackLabel ?? 'Output pack'
}

export type TargetOutputPackPayloadV1 = {
  /** Methodology stage you are aiming for. */
  targetStage: TargetStage
  /** One of the five Forge output pack kinds. */
  outputPackKind: OutputPackKind
  /** When false, `packLabel` tracks the default for `outputPackKind`. */
  useCustomPackLabel: boolean
  /** Label for the primary artifact pack. */
  packLabel: string
  /** One non-empty line per artifact or deliverable row. */
  artifactLines: string
}

export function emptyTargetOutputPackPayload(): TargetOutputPackPayloadV1 {
  const kind: OutputPackKind = 'foundation_pack'
  return {
    targetStage: 'idea',
    outputPackKind: kind,
    useCustomPackLabel: false,
    packLabel: defaultPackLabelForKind(kind),
    artifactLines: '',
  }
}

function isStr(v: unknown): v is string {
  return typeof v === 'string'
}

export function parseTargetOutputPackFromPayload(
  payload: Record<string, unknown>,
  fallbackStage: TargetStage,
): TargetOutputPackPayloadV1 {
  const raw = payload.targetOutputPack
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    return { ...emptyTargetOutputPackPayload(), targetStage: fallbackStage }
  }
  const o = raw as Record<string, unknown>
  const targetStage = isTargetStage(o.targetStage) ? o.targetStage : fallbackStage
  const outputPackKind: OutputPackKind = isOutputPackKind(o.outputPackKind) ? o.outputPackKind : 'foundation_pack'
  const useCustomPackLabel = o.useCustomPackLabel === true
  let packLabel = isStr(o.packLabel) ? o.packLabel : defaultPackLabelForKind(outputPackKind)
  if (!useCustomPackLabel) {
    packLabel = defaultPackLabelForKind(outputPackKind)
  }
  const artifactLines = isStr(o.artifactLines) ? o.artifactLines : ''
  return {
    targetStage,
    outputPackKind,
    useCustomPackLabel,
    packLabel: packLabel.slice(0, TARGET_PACK_LABEL_MAX),
    artifactLines: artifactLines.slice(0, TARGET_ARTIFACT_LINES_MAX),
  }
}

export type TargetOutputPackFieldErrors = {
  targetStage?: string
  packLabel?: string
  artifactLines?: string
  outputPackKind?: string
}

export function validateTargetOutputPackForNext(t: TargetOutputPackPayloadV1): {
  ok: boolean
  errors: TargetOutputPackFieldErrors
} {
  const errors: TargetOutputPackFieldErrors = {}
  if (!isTargetStage(t.targetStage)) {
    errors.targetStage = 'Pick a target stage.'
  }
  if (!isOutputPackKind(t.outputPackKind)) {
    errors.outputPackKind = 'Pick an output pack kind.'
  }
  const label = t.packLabel.trim()
  if (!label) {
    errors.packLabel = 'Name the output pack (e.g. handbook slice, ceremony pack).'
  } else if (label.length > TARGET_PACK_LABEL_MAX) {
    errors.packLabel = `Pack label must be at most ${TARGET_PACK_LABEL_MAX} characters.`
  }
  const lines = t.artifactLines
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean)
  if (lines.length === 0) {
    errors.artifactLines = 'Add at least one artifact or deliverable line.'
  } else if (t.artifactLines.length > TARGET_ARTIFACT_LINES_MAX) {
    errors.artifactLines = `Artifact list must be at most ${TARGET_ARTIFACT_LINES_MAX} characters.`
  }
  return { ok: Object.keys(errors).length === 0, errors }
}

export function clampTargetOutputPackPayload(t: TargetOutputPackPayloadV1): TargetOutputPackPayloadV1 {
  const kind: OutputPackKind = isOutputPackKind(t.outputPackKind) ? t.outputPackKind : 'foundation_pack'
  const stage: TargetStage = isTargetStage(t.targetStage) ? t.targetStage : 'idea'
  const useCustom = t.useCustomPackLabel === true
  const labelBase = useCustom ? t.packLabel : defaultPackLabelForKind(kind)
  return {
    targetStage: stage,
    outputPackKind: kind,
    useCustomPackLabel: useCustom,
    packLabel: labelBase.slice(0, TARGET_PACK_LABEL_MAX),
    artifactLines: t.artifactLines.slice(0, TARGET_ARTIFACT_LINES_MAX),
  }
}

function newPackItemId(packId: string, index: number): string {
  return `${packId.slice(0, 64)}-i${index}`
}

function randomPackId(): string {
  const a = new Uint8Array(8)
  crypto.getRandomValues(a)
  return `pack_${Array.from(a, (b) => b.toString(16).padStart(2, '0')).join('')}`
}

/** Builds a single primary artifact pack for `wizard_domain.artifact_packs`. */
export function artifactPackFromTargetPayload(
  t: TargetOutputPackPayloadV1,
  existingPackId?: string,
): ArtifactPackJson {
  const id =
    existingPackId && existingPackId.trim().length > 0
      ? existingPackId.trim().slice(0, 128)
      : randomPackId()
  const lines = t.artifactLines
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean)
  const items = lines.map((label, i) => ({
    id: newPackItemId(id, i),
    label: label.slice(0, 500),
    status: 'draft' as const,
  }))
  return {
    id,
    label: t.packLabel.trim().slice(0, 500) || 'Output pack',
    items,
  }
}

/** When `payload.targetOutputPack` is absent, derive from `wizard_domain` (domain-only sessions). */
export function targetOutputPackFromPayloadOrDomain(
  payload: Record<string, unknown>,
  wd: WizardDomainJson,
): TargetOutputPackPayloadV1 {
  if (payload.targetOutputPack && typeof payload.targetOutputPack === 'object' && !Array.isArray(payload.targetOutputPack)) {
    return clampTargetOutputPackPayload(
      parseTargetOutputPackFromPayload(payload, (wd.target_stage as TargetStage) || 'idea'),
    )
  }
  const stage = isTargetStage(wd.target_stage) ? wd.target_stage : 'idea'
  const pack = wd.artifact_packs?.[0]
  const lines = pack?.items?.map((it) => it.label).join('\n') ?? ''
  return clampTargetOutputPackPayload({
    ...emptyTargetOutputPackPayload(),
    targetStage: stage,
    packLabel: pack?.label ?? defaultPackLabelForKind('foundation_pack'),
    artifactLines: lines,
  })
}

export function formatTargetOutputPackForStepNote(t: TargetOutputPackPayloadV1): string {
  const lines: string[] = []
  const st = TARGET_STAGE_UI[t.targetStage]?.forgeLabel ?? t.targetStage
  lines.push(`Target stage: ${st} (${t.targetStage})`)
  const pk = OUTPUT_PACK_KIND_UI[t.outputPackKind]?.forgeLabel ?? t.outputPackKind
  lines.push(`Output pack kind: ${pk}`)
  lines.push(`Pack label: ${t.packLabel.trim()}`)
  const al = t.artifactLines
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean)
  if (al.length) lines.push(`Artifacts:\n${al.map((x) => `- ${x}`).join('\n')}`)
  return lines.join('\n\n')
}
