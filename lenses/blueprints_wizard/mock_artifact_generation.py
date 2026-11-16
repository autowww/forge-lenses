"""Deterministic artifact bundle for tests and LENSES_ARTIFACT_GENERATION_MOCK."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lenses.blueprints_wizard.artifact_generation_normalize import (
    ARTIFACT_SLICE_KEYS,
    QUALITY_DIMENSIONS,
    normalize_provenance,
    normalize_quality_rubric,
    normalize_single_artifact_record,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _mock_quality() -> dict[str, Any]:
    q: dict[str, Any] = {}
    for dim in QUALITY_DIMENSIONS:
        q[dim] = {"score": 0.75, "rationale": f"mock_{dim}"}
    return normalize_quality_rubric(q)


def mock_artifact_bundle_partial(keys: frozenset[str] | None) -> dict[str, Any]:
    """Build normalized artifact records for keys (or all slice keys if None)."""
    want = set(ARTIFACT_SLICE_KEYS) if keys is None else set(keys) & set(ARTIFACT_SLICE_KEYS)
    out: dict[str, Any] = {}
    prov = normalize_provenance(
        {
            "generation_id": "mock-gen-1",
            "created_at": _utc_now(),
            "provider": "mock",
            "model": "mock-model",
            "input_fingerprint": "mock-fp",
        }
    )
    if "foundation_brief_final" in want:
        raw = {
            "content": {"markdown": "# Mock Foundation Brief\n\nFinalized content."},
            "quality": _mock_quality(),
            "review_status": "pending",
            "locked": False,
            "feedback": "",
            "provenance": prov,
        }
        out["foundation_brief_final"] = normalize_single_artifact_record("foundation_brief_final", raw)
    if "assumptions_ledger" in want:
        raw = {
            "content": {
                "entries": [
                    {
                        "id": "a1",
                        "text": "Mock assumption",
                        "source": "other",
                        "created_at": _utc_now(),
                        "status": "open",
                    }
                ]
            },
            "quality": _mock_quality(),
            "review_status": "pending",
            "locked": False,
            "feedback": "",
            "provenance": prov,
        }
        out["assumptions_ledger"] = normalize_single_artifact_record("assumptions_ledger", raw)
    if "roadmap" in want:
        raw = {
            "content": {
                "summary": "Mock roadmap",
                "themes": [{"title": "Theme A", "description": "d", "outcomes": ["o1"]}],
                "horizons": [{"label": "Q1", "notes": "n"}],
                "trace_refs": ["brief:problem"],
            },
            "quality": _mock_quality(),
            "review_status": "pending",
            "locked": False,
            "feedback": "",
            "provenance": prov,
        }
        out["roadmap"] = normalize_single_artifact_record("roadmap", raw)
    if "milestone_outline" in want:
        raw = {
            "content": {
                "milestones": [
                    {
                        "id": "m1",
                        "title": "Milestone 1",
                        "target": "T0",
                        "dependencies": [],
                        "success_criteria": "Done",
                        "notes": "",
                    }
                ],
                "trace_refs": [],
            },
            "quality": _mock_quality(),
            "review_status": "pending",
            "locked": False,
            "feedback": "",
            "provenance": prov,
        }
        out["milestone_outline"] = normalize_single_artifact_record("milestone_outline", raw)
    if "milestone_charters" in want:
        raw = {
            "content": {
                "charters": [
                    {
                        "id": "ch1",
                        "milestone_ref": "m1",
                        "scope": "Mock charter scope",
                        "exit_criteria": "Criteria met",
                        "notes": "",
                    }
                ],
                "trace_refs": [],
            },
            "quality": _mock_quality(),
            "review_status": "pending",
            "locked": False,
            "feedback": "",
            "provenance": prov,
        }
        out["milestone_charters"] = normalize_single_artifact_record("milestone_charters", raw)
    if "wbe_tree" in want:
        raw = {
            "content": {
                "nodes": [
                    {"id": "w1", "title": "Root WBE", "parent_id": "", "estimate": "M", "notes": ""},
                    {"id": "w2", "title": "Child", "parent_id": "w1", "estimate": "S", "notes": ""},
                ],
                "trace_refs": [],
            },
            "quality": _mock_quality(),
            "review_status": "pending",
            "locked": False,
            "feedback": "",
            "provenance": prov,
        }
        out["wbe_tree"] = normalize_single_artifact_record("wbe_tree", raw)
    if "dependency_map" in want:
        raw = {
            "content": {
                "edges": [{"from_ref": "w1", "to_ref": "w2", "dep_type": "blocks", "team": "", "notes": ""}],
                "trace_refs": [],
            },
            "quality": _mock_quality(),
            "review_status": "pending",
            "locked": False,
            "feedback": "",
            "provenance": prov,
        }
        out["dependency_map"] = normalize_single_artifact_record("dependency_map", raw)
    if "prd" in want:
        raw = {
            "content": {
                "summary": "Mock PRD summary",
                "goals": "Goals",
                "personas": "Users",
                "scope_in": "In",
                "scope_out": "Out",
                "user_stories": ["As a user, I want X"],
                "trace_refs": [],
            },
            "quality": _mock_quality(),
            "review_status": "pending",
            "locked": False,
            "feedback": "",
            "provenance": prov,
        }
        out["prd"] = normalize_single_artifact_record("prd", raw)
    if "architecture_brief" in want:
        raw = {
            "content": {
                "context": "System context",
                "containers": "App, API",
                "components": ["Auth"],
                "interfaces": [{"name": "REST", "contract": "JSON"}],
                "risks": "",
                "trace_refs": [],
            },
            "quality": _mock_quality(),
            "review_status": "pending",
            "locked": False,
            "feedback": "",
            "provenance": prov,
        }
        out["architecture_brief"] = normalize_single_artifact_record("architecture_brief", raw)
    if "nfr_checklist" in want:
        raw = {
            "content": {
                "rows": [
                    {
                        "category": "security",
                        "requirement": "AuthN",
                        "measure": "OAuth",
                        "status": "planned",
                    }
                ],
                "policy_notes": [],
                "trace_refs": [],
            },
            "quality": _mock_quality(),
            "review_status": "pending",
            "locked": False,
            "feedback": "",
            "provenance": prov,
        }
        out["nfr_checklist"] = normalize_single_artifact_record("nfr_checklist", raw)
    if "adr_seeds" in want:
        raw = {
            "content": {
                "decisions": [
                    {
                        "id": "adr1",
                        "title": "Use Postgres",
                        "context": "Need persistence",
                        "options": "A, B",
                        "decision_stub": "TBD",
                    }
                ],
                "trace_refs": [],
            },
            "quality": _mock_quality(),
            "review_status": "pending",
            "locked": False,
            "feedback": "",
            "provenance": prov,
        }
        out["adr_seeds"] = normalize_single_artifact_record("adr_seeds", raw)
    if "ownership_review_matrix" in want:
        raw = {
            "content": {
                "rows": [
                    {
                        "area": "API",
                        "owner": "Team A",
                        "reviewer": "Team B",
                        "raci": "R/A",
                        "handoff_notes": "",
                        "policy_placeholder": "",
                    }
                ],
                "policy_notes": [],
                "trace_refs": [],
            },
            "quality": _mock_quality(),
            "review_status": "pending",
            "locked": False,
            "feedback": "",
            "provenance": prov,
        }
        out["ownership_review_matrix"] = normalize_single_artifact_record("ownership_review_matrix", raw)
    if "sparks_plan" in want:
        raw = {
            "content": {
                "sparks": [
                    {
                        "spark_id": "M1E1S1T1",
                        "story_ref": "M1E1S1",
                        "phase_prefix": "build:",
                        "intent": "Mock spark intent",
                        "status": "active",
                        "notes": "",
                    }
                ],
                "trace_refs": ["wbe:w1"],
            },
            "quality": _mock_quality(),
            "review_status": "pending",
            "locked": False,
            "feedback": "",
            "provenance": prov,
        }
        out["sparks_plan"] = normalize_single_artifact_record("sparks_plan", raw)
    if "charge_plan" in want:
        raw = {
            "content": {
                "charges": [
                    {
                        "charge_id": "chg1",
                        "spark_refs": ["M1E1S1T1"],
                        "owner": "mock-owner",
                        "energy": "high",
                        "notes": "",
                    }
                ],
                "iteration_note": "Mock iteration",
                "trace_refs": [],
            },
            "quality": _mock_quality(),
            "review_status": "pending",
            "locked": False,
            "feedback": "",
            "provenance": prov,
        }
        out["charge_plan"] = normalize_single_artifact_record("charge_plan", raw)
    if "implementation_tasklets" in want:
        raw = {
            "content": {
                "tasklets": [
                    {
                        "id": "tl1",
                        "title": "Mock tasklet",
                        "detail": "Do the thing",
                        "estimate": "S",
                        "notes": "",
                        "upstream_artifacts": [
                            {"artifact_key": "prd", "generation_id": "", "wbe_node_id": "w2"}
                        ],
                    }
                ],
                "trace_refs": [],
            },
            "quality": _mock_quality(),
            "review_status": "pending",
            "locked": False,
            "feedback": "",
            "provenance": prov,
        }
        out["implementation_tasklets"] = normalize_single_artifact_record("implementation_tasklets", raw)
    if "acceptance_criteria" in want:
        raw = {
            "content": {
                "criteria": [
                    {
                        "id": "ac1",
                        "statement": "Given X, when Y, then Z",
                        "tasklet_id": "tl1",
                        "story_ref": "M1E1S1",
                        "trace_refs": ["prd:scope_in"],
                    }
                ],
                "trace_refs": [],
            },
            "quality": _mock_quality(),
            "review_status": "pending",
            "locked": False,
            "feedback": "",
            "provenance": prov,
        }
        out["acceptance_criteria"] = normalize_single_artifact_record("acceptance_criteria", raw)
    if "execution_dependency_sequence" in want:
        raw = {
            "content": {
                "ordered_steps": [
                    {"step_id": "s1", "seq": 1, "ref_type": "tasklet", "ref_id": "tl1", "notes": ""}
                ],
                "trace_refs": [],
            },
            "quality": _mock_quality(),
            "review_status": "pending",
            "locked": False,
            "feedback": "",
            "provenance": prov,
        }
        out["execution_dependency_sequence"] = normalize_single_artifact_record(
            "execution_dependency_sequence", raw
        )
    if "qa_verification_checklist" in want:
        raw = {
            "content": {
                "items": [
                    {
                        "id": "q1",
                        "check": "Verify API returns 200",
                        "evidence": "curl log",
                        "tasklet_id": "tl1",
                    }
                ],
                "trace_refs": [],
            },
            "quality": _mock_quality(),
            "review_status": "pending",
            "locked": False,
            "feedback": "",
            "provenance": prov,
        }
        out["qa_verification_checklist"] = normalize_single_artifact_record(
            "qa_verification_checklist", raw
        )
    if "rollout_notes" in want:
        raw = {
            "content": {
                "sections": [{"title": "Rollout", "body": "Enable feature flag."}],
                "canary_notes": "5% canary",
                "trace_refs": [],
            },
            "quality": _mock_quality(),
            "review_status": "pending",
            "locked": False,
            "feedback": "",
            "provenance": prov,
        }
        out["rollout_notes"] = normalize_single_artifact_record("rollout_notes", raw)
    return out


class MockArtifactGenerationAdapter:
    """Implements ArtifactGenerationPort for tests."""

    def generate_bundle(
        self,
        *,
        workspace_root: Path,
        session_payload: dict[str, Any],
        provider: str,
        model_override: str | None,
        refine: bool,
        artifact_keys: frozenset[str],
    ) -> dict[str, Any]:
        arts = mock_artifact_bundle_partial(artifact_keys)
        return {"ok": True, "artifacts": arts}
