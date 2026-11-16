"""Typed wizard session documents (Blueprint Wizard experimental)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

CURRENT_VERSION = 2

_VALID_STATES = frozenset({"draft", "ready", "archived"})
_VALID_MODES = frozenset({"new_product", "existing_workspace"})
_VALID_VISIBILITY = frozenset({"public", "private"})
_VALID_ACCOUNT = frozenset({"user", "org"})


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def empty_wizard_payload() -> dict[str, Any]:
    """Default payload keys for CURRENT_VERSION (merged with any legacy keys on load)."""
    from lenses.blueprints_wizard.wizard_domain_normalize import empty_wizard_domain

    return {
        "title": "",
        "purpose": "",
        "state": "draft",
        "mode": "existing_workspace",
        "scope": {
            "wbs_rel": None,
            "roadmap_rel": None,
            "roadmap_section_id": None,
        },
        "parent_session_id": None,
        "new_product_draft": {
            "repo_name": "",
            "visibility": "private",
            "account_type": "user",
            "owner": "",
            "license": "",
            "description": "",
        },
        "created_repo_url": None,
        "wizard_domain": empty_wizard_domain(),
    }


def _coerce_str(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip()


def _coerce_opt_str(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None


def normalize_wizard_payload(raw: Any) -> dict[str, Any]:
    """Merge defaults; preserve unknown keys (stepNotes, mission, foundation_brief, …)."""
    from lenses.blueprints_wizard.wizard_domain_normalize import normalize_wizard_domain

    defaults = empty_wizard_payload()
    if not isinstance(raw, dict):
        out: dict[str, Any] = dict(defaults)
    else:
        out = {k: v for k, v in raw.items()}
        for k, dv in defaults.items():
            if k not in out:
                out[k] = dv
        if isinstance(out.get("scope"), dict):
            out["scope"] = {**defaults["scope"], **out["scope"]}
        else:
            out["scope"] = dict(defaults["scope"])
        if isinstance(out.get("new_product_draft"), dict):
            out["new_product_draft"] = {**defaults["new_product_draft"], **out["new_product_draft"]}
        else:
            out["new_product_draft"] = dict(defaults["new_product_draft"])
    st = _coerce_str(out.get("state")) or "draft"
    out["state"] = st if st in _VALID_STATES else "draft"
    md = _coerce_str(out.get("mode")) or "existing_workspace"
    out["mode"] = md if md in _VALID_MODES else "existing_workspace"
    out["title"] = _coerce_str(out.get("title"))[:500]
    out["purpose"] = _coerce_str(out.get("purpose"))[:4000]
    ps = out.get("parent_session_id")
    out["parent_session_id"] = _coerce_opt_str(ps)
    nd = out.get("new_product_draft")
    if isinstance(nd, dict):
        vis = _coerce_str(nd.get("visibility")).lower() or "private"
        nd["visibility"] = vis if vis in _VALID_VISIBILITY else "private"
        at = _coerce_str(nd.get("account_type")).lower() or "user"
        nd["account_type"] = at if at in _VALID_ACCOUNT else "user"
        nd["repo_name"] = _coerce_str(nd.get("repo_name"))[:200]
        nd["owner"] = _coerce_str(nd.get("owner"))[:200]
        nd["license"] = _coerce_str(nd.get("license"))[:120]
        nd["description"] = _coerce_str(nd.get("description"))[:8000]
    cr = out.get("created_repo_url")
    out["created_repo_url"] = _coerce_opt_str(cr) if cr is not None else None
    sc = out.get("scope")
    if isinstance(sc, dict):
        sc["wbs_rel"] = _coerce_opt_str(sc.get("wbs_rel"))
        sc["roadmap_rel"] = _coerce_opt_str(sc.get("roadmap_rel"))
        sid = sc.get("roadmap_section_id")
        sc["roadmap_section_id"] = _coerce_opt_str(sid) if sid is not None else None
    wd = out.get("wizard_domain")
    out["wizard_domain"] = normalize_wizard_domain(wd)
    return out


@dataclass
class WizardSessionDocument:
    """Session JSON: payload may include stepNotes, mission (step 0), contributionSetup (step 1), contextIntake (step 2), foundation_brief (refine)."""

    version: int
    updated_at: str
    step_index: int
    payload: dict[str, Any]

    @staticmethod
    def new_empty() -> WizardSessionDocument:
        return WizardSessionDocument(
            version=CURRENT_VERSION,
            updated_at=_utc_now_iso(),
            step_index=0,
            payload=normalize_wizard_payload({}),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> WizardSessionDocument | None:
        if not isinstance(data, dict):
            return None
        ver = data.get("version")
        step = data.get("step_index")
        if not isinstance(ver, int) or not isinstance(step, int):
            return None
        if ver < 1 or ver > CURRENT_VERSION + 5:
            return None
        updated = data.get("updated_at")
        if not isinstance(updated, str):
            return None
        raw_payload = data.get("payload")
        if raw_payload is None:
            payload_in: dict[str, Any] = {}
        elif isinstance(raw_payload, dict):
            payload_in = dict(raw_payload)
        else:
            return None
        payload = normalize_wizard_payload(payload_in)
        return WizardSessionDocument(
            version=ver,
            updated_at=updated,
            step_index=step,
            payload=payload,
        )
