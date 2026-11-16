"""Upstream approval requirements for engineering-grade artifact slices (experimental)."""

from __future__ import annotations

from typing import Any

from lenses.blueprints_wizard.artifact_generation_normalize import ARTIFACT_SLICE_KEYS

# All listed keys must be present with review_status in approved or locked.
ARTIFACT_UPSTREAM_AND: dict[str, tuple[str, ...]] = {
    "milestone_charters": ("roadmap",),
    "prd": ("foundation_brief_final", "roadmap"),
    "architecture_brief": ("foundation_brief_final", "roadmap"),
    "nfr_checklist": ("foundation_brief_final", "roadmap"),
    "dependency_map": ("wbe_tree",),
    "adr_seeds": ("architecture_brief",),
    "sparks_plan": ("wbe_tree", "prd"),
    "charge_plan": ("sparks_plan",),
    "implementation_tasklets": ("wbe_tree", "prd"),
    "execution_dependency_sequence": ("implementation_tasklets", "dependency_map"),
}

# Exactly one group must be fully satisfied (each key in the chosen group approved/locked).
ARTIFACT_UPSTREAM_ONE_OF: dict[str, tuple[tuple[str, ...], ...]] = {
    "wbe_tree": (("milestone_outline",), ("milestone_charters",)),
    "acceptance_criteria": (("implementation_tasklets",), ("prd",)),
}

# For ownership_review_matrix: at least one of these must be approved/locked.
OWNERSHIP_REQUIRES_ANY_OF: tuple[str, ...] = (
    "foundation_brief_final",
    "roadmap",
    "milestone_outline",
    "assumptions_ledger",
)

QA_VERIFICATION_REQUIRES_ANY_OF: tuple[str, ...] = ("acceptance_criteria", "nfr_checklist")

ROLLOUT_NOTES_REQUIRES_ANY_OF: tuple[str, ...] = ("qa_verification_checklist", "architecture_brief")


def _approved(rec: Any) -> bool:
    if not isinstance(rec, dict):
        return False
    rs = str(rec.get("review_status") or "").strip().lower()
    return rs in ("approved", "locked")


def _collect_upstream_lineage(
    arts: dict[str, Any],
    keys: tuple[str, ...],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for k in keys:
        if k not in ARTIFACT_SLICE_KEYS:
            continue
        rec = arts.get(k)
        if not isinstance(rec, dict):
            continue
        prov = rec.get("provenance")
        if not isinstance(prov, dict):
            continue
        gid = str(prov.get("generation_id") or "").strip()
        if not gid:
            continue
        rs = str(rec.get("review_status") or "pending").strip().lower()
        out.append({"artifact_key": k, "generation_id": gid[:128], "review_status": rs})
    return out


def upstream_keys_for_generation(artifact_keys: frozenset[str], arts: dict[str, Any]) -> frozenset[str]:
    """Union of upstream keys to record in lineage / fingerprint for this generation."""
    need: set[str] = set()
    for ak in artifact_keys:
        if ak in ARTIFACT_UPSTREAM_AND:
            need.update(ARTIFACT_UPSTREAM_AND[ak])
        if ak in ARTIFACT_UPSTREAM_ONE_OF:
            for group in ARTIFACT_UPSTREAM_ONE_OF[ak]:
                need.update(group)
        if ak == "ownership_review_matrix":
            for k in OWNERSHIP_REQUIRES_ANY_OF:
                if _approved(arts.get(k)):
                    need.add(k)
        if ak == "qa_verification_checklist":
            for k in QA_VERIFICATION_REQUIRES_ANY_OF:
                if _approved(arts.get(k)):
                    need.add(k)
        if ak == "rollout_notes":
            for k in ROLLOUT_NOTES_REQUIRES_ANY_OF:
                if _approved(arts.get(k)):
                    need.add(k)
    return frozenset(need)


def assert_upstream_approved(
    artifact_keys: frozenset[str],
    arts: dict[str, Any],
) -> tuple[bool, str | None, str | None]:
    """
    Returns (ok, error_code, detail).
    ``arts`` is ``wizard_domain.artifact_generation.artifacts`` (normalized).
    Upstream keys also listed in ``artifact_keys`` are treated as in-flight (same batch).
    """
    inflight = artifact_keys

    def _ready(k: str) -> bool:
        if k in inflight:
            return True
        return _approved(arts.get(k))

    for ak in artifact_keys:
        if ak not in ARTIFACT_SLICE_KEYS:
            continue

        if ak in ARTIFACT_UPSTREAM_AND:
            for uk in ARTIFACT_UPSTREAM_AND[ak]:
                if not _ready(uk):
                    return (
                        False,
                        "upstream_not_approved",
                        f"{ak} requires approved upstream: {uk}",
                    )

        if ak in ARTIFACT_UPSTREAM_ONE_OF:
            groups = ARTIFACT_UPSTREAM_ONE_OF[ak]
            satisfied = any(all(_ready(k) for k in group) for group in groups)
            if not satisfied:
                alts = " or ".join("(" + ", ".join(g) + ")" for g in groups)
                return (
                    False,
                    "upstream_not_approved",
                    f"{ak} requires one of: {alts}",
                )

        if ak == "ownership_review_matrix":
            if not any(_ready(k) for k in OWNERSHIP_REQUIRES_ANY_OF):
                return (
                    False,
                    "upstream_not_approved",
                    "ownership_review_matrix requires at least one approved planning artifact",
                )

        if ak == "qa_verification_checklist":
            if not any(_ready(k) for k in QA_VERIFICATION_REQUIRES_ANY_OF):
                return (
                    False,
                    "upstream_not_approved",
                    "qa_verification_checklist requires acceptance_criteria or nfr_checklist approved",
                )

        if ak == "rollout_notes":
            if not any(_ready(k) for k in ROLLOUT_NOTES_REQUIRES_ANY_OF):
                return (
                    False,
                    "upstream_not_approved",
                    "rollout_notes requires qa_verification_checklist or architecture_brief approved",
                )

    return True, None, None


def build_lineage_upstream_entries(
    artifact_keys: frozenset[str],
    arts: dict[str, Any],
) -> list[dict[str, Any]]:
    """Snapshot upstream provenance for stamps on newly generated artifacts."""
    keys = upstream_keys_for_generation(artifact_keys, arts)
    return _collect_upstream_lineage(arts, tuple(sorted(keys)))


PLANNING_SLICE_KEYS = frozenset(
    {
        "foundation_brief_final",
        "assumptions_ledger",
        "roadmap",
        "milestone_outline",
        "milestone_charters",
    }
)

ENGINEERING_SLICE_KEYS = frozenset(
    {
        "wbe_tree",
        "dependency_map",
        "prd",
        "architecture_brief",
        "nfr_checklist",
        "adr_seeds",
        "ownership_review_matrix",
    }
)

EXECUTION_SLICE_KEYS = frozenset(
    {
        "sparks_plan",
        "charge_plan",
        "implementation_tasklets",
        "acceptance_criteria",
        "execution_dependency_sequence",
        "qa_verification_checklist",
        "rollout_notes",
    }
)

PLANNING_ENGINEERING_KEYS = frozenset(PLANNING_SLICE_KEYS) | frozenset(ENGINEERING_SLICE_KEYS)


def resolve_requested_artifact_keys(body: dict[str, Any]) -> tuple[frozenset[str] | None, str | None]:
    """
    Returns (keys or None for legacy full-planning default, error_detail).
    ``artifact_keys`` list wins, then ``artifact``, then ``artifact_bundle``, else planning bundle.
    """
    raw_list = body.get("artifact_keys")
    if isinstance(raw_list, list) and len(raw_list) > 0:
        keys: set[str] = set()
        for x in raw_list:
            k = str(x).strip()
            if k and k in ARTIFACT_SLICE_KEYS:
                keys.add(k)
        if not keys:
            return None, "invalid_artifact_keys"
        return frozenset(keys), None

    art_raw = body.get("artifact")
    if art_raw is not None and str(art_raw).strip() != "":
        key = str(art_raw).strip()
        if key not in ARTIFACT_SLICE_KEYS:
            return None, key
        return frozenset({key}), None

    bundle = str(body.get("artifact_bundle") or "").strip().lower()
    if bundle == "engineering":
        return frozenset(ENGINEERING_SLICE_KEYS), None
    if bundle == "planning":
        return frozenset(PLANNING_SLICE_KEYS), None
    if bundle == "execution":
        return frozenset(EXECUTION_SLICE_KEYS), None
    if bundle in ("all", "full"):
        return frozenset(PLANNING_ENGINEERING_KEYS), None
    if bundle in ("complete", "full_stack"):
        return frozenset(ARTIFACT_SLICE_KEYS), None

    # Default: planning slice (size-friendly; mirrors former 4-key focus + milestone_charters).
    return frozenset(PLANNING_SLICE_KEYS), None
