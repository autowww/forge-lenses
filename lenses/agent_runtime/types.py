"""JSON-serializable shapes for agent runtime (DOCS-3)."""

from __future__ import annotations

from typing import Any, Literal, TypedDict


PrivacyLevel = Literal["local_only", "private_url", "cloud_allowed"]
TokenCountingMode = Literal["exact", "estimated"]
CostTier = Literal["free", "low", "medium", "high"]
HealthState = Literal["healthy", "degraded", "unavailable", "not_configured"]
CapabilityTier = Literal["small", "medium", "high"]


class EndpointCapability(TypedDict, total=False):
    """
    Semantic capability requested by tasklets (no provider/model IDs).

    IDs use ``<family>.<tier>`` (e.g. ``writer.medium``) for stable routing policy.
    """

    id: str
    label: str
    family: str  # triage | writer | reviewer
    tier: CapabilityTier
    description: str


class ProviderEndpoint(TypedDict, total=False):
    """Logical provider + transport (Ollama daemon or OpenAI-compatible base URL)."""

    id: str
    adapter: str  # "ollama" | "openai_compatible" | "anthropic" | "openai" | "gemini"
    display_name: str
    base_url_hint: str
    supports_text: bool
    supports_streaming: bool
    max_context_tokens: int
    json_mode_reliable: bool
    health: HealthState
    token_counting: TokenCountingMode
    privacy: PrivacyLevel
    cost_tier: CostTier
    latency_tier: str
    last_probe_error: str | None
    served_capabilities: list[str]


class ModelSlot(TypedDict, total=False):
    """Named routing slot (no hard-coded model IDs in business logic)."""

    id: str
    label: str
    studio_task_id: str
    preferred_privacy: PrivacyLevel
    primary_endpoint_kind: str  # "local" | "external_url" | "cloud"
    fallback_order: list[str]  # endpoint adapter ids or keywords
    capability_id: str


class DispatchPolicy(TypedDict, total=False):
    """Workspace-level dispatch rules (merged from LLM settings ``agent_runtime``)."""

    local_first: bool
    allow_cloud_escalation: bool
    allow_private_compat_url: bool
    require_loopback_for_external_url: bool
    max_escalation_steps: int


class DispatchStep(TypedDict, total=False):
    provider: str
    adapter: str
    reason: str
    skipped: bool
    skip_detail: str | None
    endpoint_id: str | None
    endpoint_health: HealthState | str | None


class DispatchTrace(TypedDict, total=False):
    slot: str
    requested_slot: str
    capability_id: str
    studio_task_id: str
    policy: DispatchPolicy
    steps_evaluated: list[DispatchStep]
    chosen_index: int | None
    fallback_used: bool


class ModelCallRecord(TypedDict, total=False):
    id: str
    ts: str
    endpoint_id: str
    provider: str
    adapter: str
    model_slot: str
    studio_task_id: str | None
    model_id: str | None
    input_tokens: int
    output_tokens: int
    total_tokens: int
    token_counting_mode: TokenCountingMode
    elapsed_ms: int
    ok: bool
    session_id: str | None
    project_slug: str | None
    scan_run_id: str | None
    cluster_id: str | None
    agent_definition_id: str | None
    dispatch_trace: DispatchTrace | None


class TokenUsageSnapshot(TypedDict, total=False):
    calls: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated: bool
    by_slot: dict[str, dict[str, Any]]
    last_slot: str | None
    last_endpoint: str | None


class SessionEvent(TypedDict, total=False):
    seq: int
    ts: str
    type: str
    payload: dict[str, Any]


class AgentDefinition(TypedDict, total=False):
    id: str
    version: int
    label: str


class AgentSession(TypedDict, total=False):
    id: str
    kind: str
    project_slug: str | None
    scan_run_id: str | None
    cluster_id: str | None
    docs_health_run_id: str | None
    agent: AgentDefinition
    status: str
    created_at: str
    updated_at: str
    events: list[SessionEvent]
    usage: TokenUsageSnapshot
    metadata: dict[str, Any]


def default_dispatch_policy(raw: dict[str, Any] | None) -> DispatchPolicy:
    ar = raw.get("agent_runtime") if isinstance(raw, dict) and isinstance(raw.get("agent_runtime"), dict) else {}
    return {
        "local_first": bool(ar.get("local_first", True)),
        "allow_cloud_escalation": bool(ar.get("allow_cloud_escalation", True)),
        "allow_private_compat_url": bool(ar.get("allow_private_compat_url", True)),
        "require_loopback_for_external_url": bool(ar.get("require_loopback_for_external_url", True)),
        "max_escalation_steps": int(ar.get("max_escalation_steps") or 4),
    }
