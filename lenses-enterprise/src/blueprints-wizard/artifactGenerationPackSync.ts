/**
 * Sync artifact pack item statuses from `wizard_domain.artifact_generation` (client merge).
 * Stale detection (input fingerprint drift) is applied on the server; here we map review → draft/ready.
 */

import { normalizeArtifactPack } from './wizardDomainNormalize'
import type {
  ArtifactPackJson,
  ArtifactSliceKey,
  ArtifactStatus,
  GeneratedArtifactRecordJson,
  WizardDomainJson,
} from './wizardDomainTypes'
import { ARTIFACT_SLICE_DISPLAY_LABELS, ARTIFACT_SLICE_KEYS } from './wizardDomainTypes'

function normLabel(s: string): string {
  return s
    .trim()
    .toLowerCase()
    .replace(/\s+/g, ' ')
}

export function sliceKeyForPackLabel(label: string): ArtifactSliceKey | null {
  const n = normLabel(label)
  if (!n) return null
  if (n.includes('ownership') && (n.includes('matrix') || n.includes('raci') || n.includes('review')))
    return 'ownership_review_matrix'
  if (n.includes('adr') || (n.includes('design') && n.includes('decision'))) return 'adr_seeds'
  if (n.includes('nfr') || (n.includes('non') && n.includes('functional'))) return 'nfr_checklist'
  if (n.includes('architecture') || n.includes('arch brief')) return 'architecture_brief'
  if (n === 'prd' || n.includes('product requirements')) return 'prd'
  if (n.includes('dependency') || n.includes('dep map')) return 'dependency_map'
  if (n.includes('wbe') || n.includes('work breakdown')) return 'wbe_tree'
  if (n.includes('milestone') && n.includes('charter')) return 'milestone_charters'
  if (n.includes('milestone') && n.includes('outline')) return 'milestone_outline'
  if (n.includes('roadmap')) return 'roadmap'
  if (n.includes('assumption') && n.includes('ledger')) return 'assumptions_ledger'
  if (n.includes('foundation') && n.includes('brief') && n.includes('final')) return 'foundation_brief_final'
  if (n === 'roadmap') return 'roadmap'
  if (n === 'milestone outline') return 'milestone_outline'
  if (n === 'assumptions ledger') return 'assumptions_ledger'
  if (n.includes('rollout')) return 'rollout_notes'
  if (n.includes('qa') || n.includes('verification')) return 'qa_verification_checklist'
  if (n.includes('execution') && (n.includes('sequence') || n.includes('ordered'))) {
    return 'execution_dependency_sequence'
  }
  if (n.includes('acceptance')) return 'acceptance_criteria'
  if (n.includes('tasklet')) return 'implementation_tasklets'
  if (n.includes('charge') && n.includes('plan')) return 'charge_plan'
  if (n.includes('spark') && n.includes('plan')) return 'sparks_plan'
  return null
}

function statusFromRecordClient(rec: GeneratedArtifactRecordJson): ArtifactStatus | string {
  const rs = String(rec.review_status || 'pending').toLowerCase()
  if (rs === 'approved' || rs === 'locked') return 'ready'
  return 'draft'
}

/**
 * Apply generation review state to pack items whose labels map to planning slices.
 */
export function applyArtifactGenerationToArtifactPack(
  pack: ArtifactPackJson,
  wizardDomain: WizardDomainJson,
): ArtifactPackJson {
  const ag = wizardDomain.artifact_generation
  const arts = ag?.artifacts ?? {}
  const items = pack.items.map((it) => {
    const sk = sliceKeyForPackLabel(it.label)
    if (!sk || !ARTIFACT_SLICE_KEYS.includes(sk)) {
      return { ...it }
    }
    const rec = arts[sk] as GeneratedArtifactRecordJson | undefined
    if (!rec) {
      return { ...it, status: 'draft' as const }
    }
    return {
      ...it,
      status: statusFromRecordClient(rec) as ArtifactStatus,
    }
  })
  return normalizeArtifactPack({ ...pack, items })
}

/** Lines for Run Plan preview — artifact review snapshot. */
export function artifactGenerationPreviewLines(wd: WizardDomainJson | null | undefined): string[] {
  if (!wd?.artifact_generation?.artifacts) return []
  const lines: string[] = []
  for (const key of ARTIFACT_SLICE_KEYS) {
    const rec = wd.artifact_generation.artifacts[key]
    if (!rec) continue
    lines.push(
      `${ARTIFACT_SLICE_DISPLAY_LABELS[key]}: ${String(rec.review_status)} (align pack line label for row status)`,
    )
  }
  return lines
}
