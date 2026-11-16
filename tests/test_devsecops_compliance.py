"""DevSecOps, policy-as-code, and CICD merge (Sprint 6)."""

from __future__ import annotations

from pathlib import Path

import pytest

from lenses.cicd_orchestration.aggregate import build_cicd_control_tower_payload
from lenses.devsecops_compliance.aggregate import build_devsecops_overview_payload, build_project_devsecops_payload
from lenses.devsecops_compliance.feature_flag import experimental_devsecops_compliance_enabled
from lenses.devsecops_compliance.local_store import load_demo_fixture
from lenses.devsecops_compliance.policy_engine import evaluate_security_policy_checks, security_policy_promotion_blockers
from lenses.devsecops_compliance.story_evidence import story_devsecops_evidence_from_doc


def test_devsecops_disabled(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LENSES_EXPERIMENTAL_DEVSECOPS_COMPLIANCE", "0")
    assert experimental_devsecops_compliance_enabled() is False
    scan = {"children": [], "resolved_at": "t"}
    out = build_devsecops_overview_payload(workspace_root=tmp_path, scan_state=scan, force_flag=False)
    assert out["feature_enabled"] is False


def test_devsecops_demo_seed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("LENSES_EXPERIMENTAL_DEVSECOPS_COMPLIANCE", raising=False)
    monkeypatch.setenv("LENSES_DEVSECOPS_COMPLIANCE_SEED_DEMO", "1")
    scan = {"children": [{"name": "forgesdlc", "is_git": True}], "resolved_at": "t"}
    out = build_devsecops_overview_payload(workspace_root=tmp_path, scan_state=scan, force_flag=True)
    assert out["feature_enabled"] is True
    assert out["provider_kind"] == "local_fixture"
    assert len(out.get("security_findings") or []) >= 1
    rs = out.get("risk_score") or {}
    assert "value" in rs
    assert isinstance(rs.get("breakdown"), dict)
    gate = out.get("security_release_gate") or {}
    assert "passed" in gate
    failed = [e for e in out.get("policy_check_evaluations") or [] if not e.get("passed")]
    assert len(failed) >= 1


def test_security_policies_block_promotions(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LENSES_DEVSECOPS_COMPLIANCE_SEED_DEMO", "1")
    lenses_root = Path(__file__).resolve().parent.parent / "lenses"
    doc = load_demo_fixture(lenses_root)
    assert doc is not None
    from lenses.devsecops_compliance.ingest import expand_ingestions

    doc = expand_ingestions(doc)
    ev = evaluate_security_policy_checks(doc, now_iso="2026-04-11T12:00:00Z")
    promos = [
        {"id": "promo-stg-prod-1", "from_env": "staging", "to_env": "production"},
        {"id": "promo-dev-stg-1", "from_env": "dev", "to_env": "staging"},
    ]
    blocked = security_policy_promotion_blockers(ev, promos)
    reasons = {str(b.get("reason")) for b in blocked}
    assert any(r.startswith("security_policy_failed:") for r in reasons)


def test_cicd_merges_security_blockers(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LENSES_CICD_ORCHESTRATION_SEED_DEMO", "1")
    monkeypatch.setenv("LENSES_DEVSECOPS_COMPLIANCE_SEED_DEMO", "1")
    scan = {"children": [{"name": "forgesdlc", "is_git": True}], "resolved_at": "t"}
    out = build_cicd_control_tower_payload(workspace_root=tmp_path, scan_state=scan, force_flag=True)
    assert "security_release_gate" in out
    reasons = [str(b.get("reason")) for b in out.get("blocked_promotions") or []]
    assert any(r.startswith("security_policy_failed:") for r in reasons)


def test_project_devsecops_payload(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LENSES_DEVSECOPS_COMPLIANCE_SEED_DEMO", "1")
    scan = {"children": [{"name": "forgesdlc", "is_git": True}], "resolved_at": "t"}
    out = build_project_devsecops_payload(
        workspace_root=tmp_path,
        scan_state=scan,
        project_name="forgesdlc",
        force_flag=True,
    )
    assert out.get("security_summary") is not None
    assert (out["security_summary"].get("risk_score") or {}).get("value") is not None


def test_story_devsecops_evidence_s1842(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LENSES_DEVSECOPS_COMPLIANCE_SEED_DEMO", "1")
    lenses_root = Path(__file__).resolve().parent.parent / "lenses"
    doc = load_demo_fixture(lenses_root)
    assert doc is not None
    from lenses.devsecops_compliance.ingest import expand_ingestions

    doc = expand_ingestions(doc)
    ev = story_devsecops_evidence_from_doc(doc, "S-1842")
    assert ev["ok"] is True
    assert len(ev.get("security_findings") or []) >= 1
    assert len(ev.get("exceptions") or []) >= 1
    assert len(ev.get("controls") or []) >= 1
