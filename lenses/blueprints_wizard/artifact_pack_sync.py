"""Sync ``artifact_packs`` item statuses from ``artifact_generation`` (planning slice)."""

from __future__ import annotations

from typing import Any

from lenses.blueprints_wizard.artifact_generation_normalize import ARTIFACT_SLICE_KEYS, normalize_artifact_generation
from lenses.blueprints_wizard.schemas import WizardSessionDocument
from lenses.blueprints_wizard.artifact_generation_inputs import canonical_inputs_fingerprint_payload
from lenses.blueprints_wizard.domain_enums import coerce_artifact_status
from lenses.blueprints_wizard.wizard_domain_normalize import normalize_artifact_pack


def _norm_label(s: str) -> str:
    return " ".join(str(s).strip().lower().split())


def slice_key_for_pack_label(label: str) -> str | None:
    """Return slice key if ``label`` matches a known planning or engineering artifact line."""
    n = _norm_label(label)
    if not n:
        return None
    if "ownership" in n and ("matrix" in n or "raci" in n or "review" in n):
        return "ownership_review_matrix"
    if "adr" in n or ("design" in n and "decision" in n):
        return "adr_seeds"
    if "nfr" in n or ("non" in n and "functional" in n):
        return "nfr_checklist"
    if "architecture" in n or "arch brief" in n:
        return "architecture_brief"
    if n == "prd" or "product requirements" in n:
        return "prd"
    if "dependency" in n or "dep map" in n:
        return "dependency_map"
    if "wbe" in n or "work breakdown" in n:
        return "wbe_tree"
    if "milestone" in n and "charter" in n:
        return "milestone_charters"
    if "milestone" in n and "outline" in n:
        return "milestone_outline"
    if "roadmap" in n:
        return "roadmap"
    if "assumption" in n and "ledger" in n:
        return "assumptions_ledger"
    if "foundation" in n and "brief" in n and "final" in n:
        return "foundation_brief_final"
    # Single-token fallbacks (short lines)
    if n in ("roadmap",):
        return "roadmap"
    if n in ("milestone outline",):
        return "milestone_outline"
    if "assumptions ledger" in n or n == "assumptions ledger":
        return "assumptions_ledger"
    if "foundation brief" in n and "final" in n:
        return "foundation_brief_final"
    if "rollout" in n:
        return "rollout_notes"
    if "qa" in n or "verification" in n:
        return "qa_verification_checklist"
    if "execution" in n and ("sequence" in n or "ordered" in n):
        return "execution_dependency_sequence"
    if "acceptance" in n:
        return "acceptance_criteria"
    if "tasklet" in n:
        return "implementation_tasklets"
    if "charge" in n and "plan" in n:
        return "charge_plan"
    if "spark" in n and "plan" in n:
        return "sparks_plan"
    return None


def _status_from_artifact_record(
    rec: dict[str, Any],
    *,
    current_fingerprint: str,
) -> str:
    """Map generation record → artifact pack status: draft | ready | stale | rejected."""
    rs = str(rec.get("review_status") or "pending").strip().lower()
    prov = rec.get("provenance") if isinstance(rec.get("provenance"), dict) else {}
    gen_fp = str(prov.get("input_fingerprint") or "").strip()
    stale = bool(gen_fp and current_fingerprint and gen_fp != current_fingerprint)
    if rs in ("approved", "locked"):
        if stale:
            return "stale"
        return "ready"
    if rs == "changes_requested":
        return "draft"
    return "draft"


def sync_artifact_pack_items_from_generation(
    wizard_domain: dict[str, Any],
    session_payload: dict[str, Any],
) -> dict[str, Any]:
    """
    Return a shallow-updated ``wizard_domain`` copy with ``artifact_packs[0].items`` statuses
    derived from ``artifact_generation`` when labels match slice keys.
    """
    wd = dict(wizard_domain) if isinstance(wizard_domain, dict) else {}
    ag = normalize_artifact_generation(wd.get("artifact_generation"))
    arts = ag.get("artifacts") or {}
    fp = canonical_inputs_fingerprint_payload(session_payload, include_execution_scope=True)

    packs_raw = wd.get("artifact_packs")
    if not isinstance(packs_raw, list) or not packs_raw:
        return wd

    primary = normalize_artifact_pack(packs_raw[0])
    items_raw = primary.get("items")
    if not isinstance(items_raw, list):
        return wd

    new_items: list[dict[str, Any]] = []
    for it in items_raw:
        if not isinstance(it, dict):
            continue
        label = str(it.get("label") or "")
        sk = slice_key_for_pack_label(label)
        if sk is None or sk not in ARTIFACT_SLICE_KEYS:
            new_items.append(
                {
                    "id": str(it.get("id") or "")[:128],
                    "label": str(it.get("label") or "")[:500],
                    "status": coerce_artifact_status(it.get("status")),
                }
            )
            continue
        rec = arts.get(sk)
        if not isinstance(rec, dict):
            new_items.append(
                {
                    "id": str(it.get("id") or "")[:128],
                    "label": str(it.get("label") or "")[:500],
                    "status": "draft",
                }
            )
            continue
        st = _status_from_artifact_record(rec, current_fingerprint=fp)
        new_items.append(
            {
                "id": str(it.get("id") or "")[:128],
                "label": str(it.get("label") or "")[:500],
                "status": st,
            }
        )

    primary = dict(primary)
    primary["items"] = new_items
    out_packs = [normalize_artifact_pack(primary)]
    if len(packs_raw) > 1:
        out_packs.extend(normalize_artifact_pack(p) for p in packs_raw[1:] if isinstance(p, dict))
    wd = dict(wd)
    wd["artifact_packs"] = out_packs
    return wd


def apply_pack_sync_to_document(doc: WizardSessionDocument) -> WizardSessionDocument:
    """Merge synced artifact pack item statuses into the session document."""
    from lenses.blueprints_wizard.wizard_session_state import get_wizard_domain, merge_wizard_domain

    wd = get_wizard_domain(doc)
    synced = sync_artifact_pack_items_from_generation(wd, doc.payload)
    return merge_wizard_domain(doc, {"artifact_packs": synced.get("artifact_packs", [])})
