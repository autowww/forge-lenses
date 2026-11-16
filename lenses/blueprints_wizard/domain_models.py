"""Dataclass views over wizard domain JSON (experimental). Serialization uses the same dict shapes as ``wizard_domain_normalize``."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from lenses.blueprints_wizard import wizard_domain_normalize as wd


@dataclass
class FoundationBrief:
    markdown: str = ""
    field_statuses: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(raw: Any) -> FoundationBrief:
        d = wd.normalize_foundation_brief(raw)
        return FoundationBrief(
            markdown=d.get("markdown", ""),
            field_statuses=dict(d.get("field_statuses") or {}),
        )


@dataclass
class AssumptionLedgerEntry:
    id: str = ""
    text: str = ""
    source: str | None = None
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(raw: Any) -> AssumptionLedgerEntry | None:
        d = wd.normalize_assumption_ledger_entry(raw)
        if d is None:
            return None
        return AssumptionLedgerEntry(
            id=d.get("id", ""),
            text=d.get("text", ""),
            source=d.get("source"),
            created_at=d.get("created_at", ""),
        )


@dataclass
class ArtifactPackItem:
    id: str = ""
    label: str = ""
    status: str = "missing"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ArtifactPack:
    id: str = ""
    label: str = ""
    items: list[ArtifactPackItem] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "label": self.label, "items": [asdict(i) for i in self.items]}

    @staticmethod
    def from_dict(raw: Any) -> ArtifactPack:
        d = wd.normalize_artifact_pack(raw)
        items: list[ArtifactPackItem] = []
        for it in d.get("items") or []:
            if isinstance(it, dict):
                items.append(
                    ArtifactPackItem(
                        id=it.get("id", ""),
                        label=it.get("label", ""),
                        status=it.get("status", "missing"),
                    )
                )
        return ArtifactPack(id=d.get("id", ""), label=d.get("label", ""), items=items)


@dataclass
class ScopeSpec:
    summary: str = ""
    constraints_note: str = ""
    wbs_rel: str | None = None
    roadmap_rel: str | None = None
    roadmap_section_id: str | None = None
    scope_boundary: str = "full_plan"
    milestone_ref: str = ""
    wbe_path: str = ""
    capability_label: str = ""
    team_label: str = ""
    repo_paths: list[str] = field(default_factory=list)
    recheck_issue_refs: str = ""
    closure_options: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(raw: Any) -> ScopeSpec:
        d = wd.normalize_scope_spec(raw)
        return ScopeSpec(
            summary=d.get("summary", ""),
            constraints_note=d.get("constraints_note", ""),
            wbs_rel=d.get("wbs_rel"),
            roadmap_rel=d.get("roadmap_rel"),
            roadmap_section_id=d.get("roadmap_section_id"),
            scope_boundary=d.get("scope_boundary", "full_plan"),
            milestone_ref=d.get("milestone_ref", ""),
            wbe_path=d.get("wbe_path", ""),
            capability_label=d.get("capability_label", ""),
            team_label=d.get("team_label", ""),
            repo_paths=list(d.get("repo_paths") or []),
            recheck_issue_refs=d.get("recheck_issue_refs", ""),
            closure_options=list(d.get("closure_options") or []),
        )


@dataclass
class RunPlanStep:
    id: str = ""
    title: str = ""
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RunPlan:
    id: str = ""
    title: str = ""
    steps: list[RunPlanStep] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "title": self.title, "steps": [asdict(s) for s in self.steps]}

    @staticmethod
    def from_dict(raw: Any) -> RunPlan:
        d = wd.normalize_run_plan(raw)
        steps: list[RunPlanStep] = []
        for s in d.get("steps") or []:
            if isinstance(s, dict):
                steps.append(RunPlanStep(id=s.get("id", ""), title=s.get("title", ""), detail=s.get("detail", "")))
        return RunPlan(id=d.get("id", ""), title=d.get("title", ""), steps=steps)


@dataclass
class ReviewGate:
    id: str = ""
    title: str = ""
    passed: bool = False
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(raw: Any) -> ReviewGate | None:
        d = wd.normalize_review_gate(raw)
        if d is None:
            return None
        return ReviewGate(
            id=d.get("id", ""),
            title=d.get("title", ""),
            passed=bool(d.get("passed")),
            notes=d.get("notes", ""),
        )


@dataclass
class RecheckSummary:
    checked_at: str = ""
    passed: bool = False
    issues: list[str] = field(default_factory=list)
    report: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(raw: Any) -> RecheckSummary:
        d = wd.normalize_recheck_summary(raw)
        rep = d.get("report")
        return RecheckSummary(
            checked_at=d.get("checked_at", ""),
            passed=bool(d.get("passed")),
            issues=list(d.get("issues") or []),
            report=dict(rep) if isinstance(rep, dict) else {},
        )


@dataclass
class BuildPackPlan:
    format: str = "json"
    paths: list[str] = field(default_factory=list)
    notes: str = ""
    allowed_write_globs: list[str] = field(default_factory=list)
    guardrail_notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(raw: Any) -> BuildPackPlan:
        d = wd.normalize_build_pack_plan(raw)
        return BuildPackPlan(
            format=d.get("format", "json"),
            paths=list(d.get("paths") or []),
            notes=d.get("notes", ""),
            allowed_write_globs=list(d.get("allowed_write_globs") or []),
            guardrail_notes=d.get("guardrail_notes", ""),
        )


@dataclass
class PromptRecipe:
    recipe_id: str = ""
    intent: str = "clarify"
    template_ref: str = ""
    variables: dict[str, str] = field(default_factory=dict)
    prompt_mode: str = "static"
    materialization_inputs: list[str] = field(default_factory=list)
    placeholder_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(raw: Any) -> PromptRecipe:
        d = wd.normalize_prompt_recipe(raw)
        return PromptRecipe(
            recipe_id=d.get("recipe_id", ""),
            intent=d.get("intent", "clarify"),
            template_ref=d.get("template_ref", ""),
            variables=dict(d.get("variables") or {}),
            prompt_mode=d.get("prompt_mode", "static"),
            materialization_inputs=list(d.get("materialization_inputs") or []),
            placeholder_summary=d.get("placeholder_summary", ""),
        )


@dataclass
class PromptSnapshot:
    snapshot_id: str = ""
    recipe_id: str = ""
    rendered: str = ""
    content_hash: str = ""
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(raw: Any) -> PromptSnapshot | None:
        d = wd.normalize_prompt_snapshot(raw)
        if d is None:
            return None
        return PromptSnapshot(
            snapshot_id=d.get("snapshot_id", ""),
            recipe_id=d.get("recipe_id", ""),
            rendered=d.get("rendered", ""),
            content_hash=d.get("content_hash", ""),
            created_at=d.get("created_at", ""),
        )
