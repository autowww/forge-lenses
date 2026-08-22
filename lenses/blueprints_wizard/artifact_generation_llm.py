"""LLM-backed planning artifact generation using ``lenses.llm_chat``."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lenses.blueprints_wizard.artifact_generation_dependencies import EXECUTION_SLICE_KEYS
from lenses.blueprints_wizard.artifact_generation_normalize import (
    ARTIFACT_SLICE_KEYS,
    QUALITY_DIMENSIONS,
    normalize_single_artifact_record,
)
from lenses.blueprints_wizard.interpretation_normalize import extract_json_object_from_model_text
from lenses.blueprints_wizard.refine import _run_plan_markdown

# Below llm_chat.MAX_MESSAGE_CHARS (32_000).
_MAX_CONTEXT_CHARS = 28_000

_SLICE_ENUM = ", ".join(f'"{k}"' for k in ARTIFACT_SLICE_KEYS)

_JSON_INSTRUCTIONS = """You are generating planning and engineering artifacts for the Forge Blueprints Wizard.
Read the **Foundation Brief** and **Run Plan** below. Output **one JSON object only** (no markdown outside JSON).

Top-level key: "artifacts" — an object with any subset of these keys: """ + _SLICE_ENUM + """.
If asked to regenerate a single section, include **only** that key under "artifacts".

Each artifact value must be an object with:
- "content": type depends on key:
  - foundation_brief_final: { "markdown": string } — finalized Foundation Brief in Markdown.
  - assumptions_ledger: { "entries": [ { "id", "text", "source" (repo|docs|stakeholders|tickets|metrics|other), "created_at"?, "status" (open|resolved|accepted_system|marked_unknown) } ] }
  - roadmap: { "summary": string, "themes": [ { "title", "description"?, "outcomes"?: string[] } ], "horizons"?: [ { "label", "notes" } ], "trace_refs"?: string[] }
  - milestone_outline: { "milestones": [ { "id", "title", "target", "dependencies": string[], "success_criteria", "notes"? } ], "trace_refs"?: string[] }
  - milestone_charters: { "charters": [ { "id", "milestone_ref", "scope", "exit_criteria", "notes"? } ], "trace_refs"?: string[] }
  - wbe_tree: { "nodes": [ { "id", "title", "parent_id"?, "estimate"?, "notes"? } ], "trace_refs"?: string[] }
  - dependency_map: { "edges": [ { "from_ref", "to_ref", "dep_type"?, "team"?, "notes"? } ], "trace_refs"?: string[] }
  - prd: { "summary", "goals", "personas", "scope_in", "scope_out", "user_stories": string[], "trace_refs"?: string[] }
  - architecture_brief: { "context", "containers", "components": string[], "interfaces": [ { "name", "contract" } ], "risks"?, "trace_refs"?: string[] }
  - nfr_checklist: { "rows": [ { "category", "requirement", "measure", "status" } ], "policy_notes"?: string[], "trace_refs"?: string[] }
  - adr_seeds: { "decisions": [ { "id", "title", "context", "options", "decision_stub" } ], "trace_refs"?: string[] }
  - ownership_review_matrix: { "rows": [ { "area", "owner", "reviewer", "raci"?, "handoff_notes"?, "policy_placeholder"?: string } ], "policy_notes"?: string[], "trace_refs"?: string[] }
  - sparks_plan: { "sparks": [ { "spark_id", "story_ref", "phase_prefix", "intent", "status", "notes"? } ], "trace_refs"?: string[] }
  - charge_plan: { "charges": [ { "charge_id", "spark_refs": string[], "owner"?, "energy"?, "notes"? } ], "iteration_note"?, "trace_refs"?: string[] }
  - implementation_tasklets: { "tasklets": [ { "id", "title", "detail"?, "estimate"?, "notes"?, "upstream_artifacts": [ { "artifact_key", "generation_id"?, "wbe_node_id"?, "story_id"?, "spark_id"? } ] } ], "trace_refs"?: string[] } — each tasklet MUST include at least one upstream_artifacts entry with non-empty artifact_key (prd, wbe_tree, etc.).
  - acceptance_criteria: { "criteria": [ { "id", "statement", "tasklet_id"?, "story_ref"?, "trace_refs"?: string[] } ], "trace_refs"?: string[] }
  - execution_dependency_sequence: { "ordered_steps": [ { "step_id", "seq" (number), "ref_type", "ref_id", "notes"? } ], "trace_refs"?: string[] }
  - qa_verification_checklist: { "items": [ { "id", "check", "evidence"?, "tasklet_id"? } ], "trace_refs"?: string[] }
  - rollout_notes: { "sections": [ { "title", "body" } ], "canary_notes"?, "trace_refs"?: string[] }
- "quality": object with exactly these six keys: """ + ", ".join(
    f'"{d}"' for d in QUALITY_DIMENSIONS
) + """ — each maps to { "score": number between 0 and 1, "rationale": string (short) }.

Ground scores in the brief/run plan; do not invent compliance or budget facts. Prefer trace_refs as short strings pointing to brief sections or run plan steps.
When generating execution slices (sparks_plan, charge_plan, implementation_tasklets, acceptance_criteria, execution_dependency_sequence, qa_verification_checklist, rollout_notes), stay inside the **Scope context** block when present; tie sparks and tasklets to WBS/story IDs from the brief or approved engineering artifacts; produce engineering-ready tables and IDs, not generic prose.

--- Foundation Brief ---

"""

_FOOTER = """

--- Run Plan ---

"""


def _cap(s: str) -> str:
    t = (s or "").strip()
    if len(t) <= _MAX_CONTEXT_CHARS:
        return t
    return t[:_MAX_CONTEXT_CHARS] + "\n\n[truncated]"


def _contribution_depth_hint(session_payload: dict[str, Any]) -> str:
    from lenses.blueprints_wizard.domain_enums import coerce_contribution_setup_kind

    wd = session_payload.get("wizard_domain")
    if not isinstance(wd, dict):
        wd = {}
    k = coerce_contribution_setup_kind(wd.get("contribution_setup_kind"))
    hints = {
        "single": "Contribution setup: single — keep ownership matrix light (owner focus); omit cross-team dependency edges unless stated in the brief.",
        "team": "Contribution setup: team — include owner and reviewer on ownership rows; clarify handoffs.",
        "teams": "Contribution setup: teams — include team/group on dependency_map edges where relevant; explicit cross-team dependencies.",
        "enterprise": "Contribution setup: enterprise — add policy_notes (short placeholders) on nfr_checklist and ownership_review_matrix where governance applies.",
    }
    return "\n" + hints.get(k, hints["single"]) + "\n"


def run_artifact_generation_llm(
    *,
    workspace_root: Path,
    session_payload: dict[str, Any],
    provider: str,
    model_override: str | None,
    refine: bool,
    artifact_keys: frozenset[str],
) -> dict[str, Any]:
    """
    Call LLM; return ``{ ok: True, artifacts: { key: normalized record } }`` or error dict.
    """
    from lenses import llm_chat

    from lenses.blueprints_wizard.artifact_generation_inputs import effective_foundation_brief_markdown

    brief = _cap(effective_foundation_brief_markdown(session_payload))
    rp_md = _cap(_run_plan_markdown(session_payload))
    if not brief.strip() or not rp_md.strip():
        return {
            "ok": False,
            "error": "prerequisites_not_met",
            "detail": "Foundation brief and run plan text required.",
        }

    keys_s = ", ".join(sorted(artifact_keys))
    scope_hint = f"\nGenerate only these artifact keys under \"artifacts\": {keys_s}.\n"
    depth_hint = _contribution_depth_hint(session_payload)

    exec_block = ""
    if artifact_keys & EXECUTION_SLICE_KEYS:
        from lenses.blueprints_wizard.artifact_generation_execution_readiness import scope_prompt_block

        exec_block = "\n" + _cap(scope_prompt_block(session_payload)) + "\n"

    user_message = _JSON_INSTRUCTIONS + brief + _FOOTER + rp_md + exec_block + depth_hint + scope_hint

    llm_out = llm_chat.chat(
        provider,
        user_message,
        model_override,
        workspace_root=workspace_root,
        refine=refine,
        studio_task_id="plans_generation",
    )
    if not llm_out.get("ok"):
        return llm_out

    text = str(llm_out.get("text", "")).strip()
    if not text:
        return {"ok": False, "error": "empty_model_output"}

    parsed = extract_json_object_from_model_text(text)
    if parsed is None:
        return {
            "ok": False,
            "error": "artifact_generation_parse_error",
            "detail": "Model did not return valid JSON.",
        }

    arts_raw = parsed.get("artifacts")
    if not isinstance(arts_raw, dict):
        return {
            "ok": False,
            "error": "artifact_generation_parse_error",
            "detail": 'Expected top-level "artifacts" object.',
        }

    out_arts: dict[str, Any] = {}
    keys_to_read = set(artifact_keys) & set(ARTIFACT_SLICE_KEYS)

    for key in keys_to_read:
        if key not in arts_raw:
            continue
        rec = normalize_single_artifact_record(key, arts_raw.get(key))
        if rec is not None:
            out_arts[key] = rec

    if not out_arts:
        return {
            "ok": False,
            "error": "artifact_generation_parse_error",
            "detail": "No valid artifacts in model output.",
        }

    result: dict[str, Any] = {"ok": True, "artifacts": out_arts}
    if llm_out.get("model"):
        result["model"] = llm_out.get("model")
    if llm_out.get("usage"):
        result["usage"] = llm_out.get("usage")
    if llm_out.get("routing"):
        result["routing"] = llm_out.get("routing")
    return result
