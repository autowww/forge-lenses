"""String enums for Blueprints Wizard domain (experimental). Validated via frozensets + coerce helpers."""

from __future__ import annotations

from typing import Any

MISSION_TYPES = frozenset(
    {
        "explore",
        "define",
        "deliver",
        "operate",
        "sunset",
    }
)
DEFAULT_MISSION_TYPE = "explore"

CONTRIBUTION_SETUP_KINDS = frozenset({"single", "team", "teams", "enterprise"})
DEFAULT_CONTRIBUTION_SETUP_KIND = "single"

CONTEXT_SOURCES = frozenset(
    {
        "repo",
        "docs",
        "stakeholders",
        "tickets",
        "metrics",
        "other",
    }
)

INTERPRETATION_FIELD_STATUSES = frozenset(
    {
        "explicit",
        "inferred",
        "needs_confirmation",
        "unknown",
    }
)
DEFAULT_INTERPRETATION_FIELD_STATUS = "unknown"

# Forge methodology stages (stored snake_case). Legacy SDLC-style values map in coerce_target_stage.
TARGET_STAGES = frozenset(
    {
        "idea",
        "roadmap",
        "milestones",
        "wbes",
        "ore",
        "ingots",
        "sparks",
        "charges",
    }
)
DEFAULT_TARGET_STAGE = "idea"

LEGACY_TARGET_STAGE: dict[str, str] = {
    "discovery": "idea",
    "shape": "roadmap",
    "plan": "milestones",
    "build": "wbes",
    "verify": "ore",
    "release": "ingots",
    "operate": "sparks",
}

# L0–L3 autonomy. Legacy four-level map in coerce_autonomy_level.
AUTONOMY_LEVELS = frozenset(
    {
        "l0_analyst",
        "l1_drafter",
        "l2_stage_autopilot",
        "l3_goal_autopilot",
    }
)
DEFAULT_AUTONOMY_LEVEL = "l0_analyst"

LEGACY_AUTONOMY_LEVEL: dict[str, str] = {
    "suggest_only": "l0_analyst",
    "draft_with_review": "l1_drafter",
    "execute_with_gates": "l2_stage_autopilot",
    "full_autonomy": "l3_goal_autopilot",
}

MUTATION_POLICIES = frozenset(
    {
        "read_only_analysis",
        "draft_downstream_only",
        "edit_downstream_drafts",
        "regenerate_downstream_from_approved_upstream",
        "propose_upstream_only",
    }
)
DEFAULT_MUTATION_POLICY = "read_only_analysis"

LEGACY_MUTATION_POLICY: dict[str, str] = {
    "read_only": "read_only_analysis",
    "append_only": "draft_downstream_only",
    "merge_allowed": "edit_downstream_drafts",
    "replace_allowed": "regenerate_downstream_from_approved_upstream",
}

OUTPUT_PACK_KINDS = frozenset(
    {
        "foundation_pack",
        "strategy_pack",
        "planning_pack",
        "engineering_pack",
        "execution_pack",
    }
)
DEFAULT_OUTPUT_PACK_KIND = "foundation_pack"

SCOPE_BOUNDARIES = frozenset(
    {
        "full_plan",
        "milestone",
        "wbe_subtree",
        "capability",
        "team_slice",
        "repo_path",
        "recheck_subset",
    }
)
DEFAULT_SCOPE_BOUNDARY = "full_plan"

CLOSURE_OPTIONS = frozenset(
    {
        "exact_only",
        "include_required_upstream",
        "include_shared_contracts",
        "include_downstream_impacted",
        "include_verification_artifacts",
    }
)

ARTIFACT_STATUSES = frozenset(
    {
        "missing",
        "draft",
        "ready",
        "stale",
        "rejected",
    }
)
DEFAULT_ARTIFACT_STATUS = "missing"

PROMPT_INTENTS = frozenset(
    {
        "clarify",
        "expand",
        "contract",
        "recheck",
        "export",
    }
)
DEFAULT_PROMPT_INTENT = "clarify"

PROMPT_MODES = frozenset(
    {
        "static",
        "build_time_dynamic",
        "runtime_dynamic",
    }
)
DEFAULT_PROMPT_MODE = "static"

ASSUMPTION_LEDGER_STATUSES = frozenset(
    {
        "open",
        "resolved",
        "accepted_system",
        "marked_unknown",
    }
)
DEFAULT_ASSUMPTION_LEDGER_STATUS = "open"


def _coerce_str(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip()


def _norm_key(raw: Any) -> str:
    return _coerce_str(raw).lower().replace(" ", "_").replace("-", "_")


def coerce_enum(raw: Any, allowed: frozenset[str], default: str) -> str:
    s = _norm_key(raw)
    if not s:
        return default
    if s in allowed:
        return s
    return default


def coerce_mission_type(raw: Any) -> str:
    return coerce_enum(raw, MISSION_TYPES, DEFAULT_MISSION_TYPE)


def coerce_contribution_setup_kind(raw: Any) -> str:
    return coerce_enum(raw, CONTRIBUTION_SETUP_KINDS, DEFAULT_CONTRIBUTION_SETUP_KIND)


def coerce_context_source(raw: Any) -> str:
    return coerce_enum(raw, CONTEXT_SOURCES, "other")


def coerce_interpretation_field_status(raw: Any) -> str:
    return coerce_enum(raw, INTERPRETATION_FIELD_STATUSES, DEFAULT_INTERPRETATION_FIELD_STATUS)


def coerce_target_stage(raw: Any) -> str:
    s = _norm_key(raw)
    if not s:
        return DEFAULT_TARGET_STAGE
    s = LEGACY_TARGET_STAGE.get(s, s)
    if s in TARGET_STAGES:
        return s
    return DEFAULT_TARGET_STAGE


def coerce_autonomy_level(raw: Any) -> str:
    s = _norm_key(raw)
    if not s:
        return DEFAULT_AUTONOMY_LEVEL
    s = LEGACY_AUTONOMY_LEVEL.get(s, s)
    if s in AUTONOMY_LEVELS:
        return s
    return DEFAULT_AUTONOMY_LEVEL


def coerce_mutation_policy(raw: Any) -> str:
    s = _norm_key(raw)
    if not s:
        return DEFAULT_MUTATION_POLICY
    s = LEGACY_MUTATION_POLICY.get(s, s)
    if s in MUTATION_POLICIES:
        return s
    return DEFAULT_MUTATION_POLICY


def coerce_output_pack_kind(raw: Any) -> str:
    return coerce_enum(raw, OUTPUT_PACK_KINDS, DEFAULT_OUTPUT_PACK_KIND)


def coerce_scope_boundary(raw: Any) -> str:
    return coerce_enum(raw, SCOPE_BOUNDARIES, DEFAULT_SCOPE_BOUNDARY)


def normalize_closure_options_list(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    seen: set[str] = set()
    out: list[str] = []
    for x in raw:
        s = _norm_key(x)
        if not s:
            continue
        if s not in CLOSURE_OPTIONS:
            continue
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
    return sorted(out)


def coerce_artifact_status(raw: Any) -> str:
    return coerce_enum(raw, ARTIFACT_STATUSES, DEFAULT_ARTIFACT_STATUS)


def coerce_prompt_intent(raw: Any) -> str:
    return coerce_enum(raw, PROMPT_INTENTS, DEFAULT_PROMPT_INTENT)


def coerce_prompt_mode(raw: Any) -> str:
    return coerce_enum(raw, PROMPT_MODES, DEFAULT_PROMPT_MODE)


def coerce_assumption_ledger_status(raw: Any) -> str:
    return coerce_enum(raw, ASSUMPTION_LEDGER_STATUSES, DEFAULT_ASSUMPTION_LEDGER_STATUS)


ARTIFACT_REVIEW_STATUSES = frozenset(
    {
        "pending",
        "approved",
        "changes_requested",
        "locked",
    }
)
DEFAULT_ARTIFACT_REVIEW_STATUS = "pending"


def coerce_artifact_review_status(raw: Any) -> str:
    return coerce_enum(raw, ARTIFACT_REVIEW_STATUSES, DEFAULT_ARTIFACT_REVIEW_STATUS)
