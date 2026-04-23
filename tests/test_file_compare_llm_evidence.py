from __future__ import annotations

from pathlib import Path

import pytest

FIX = Path(__file__).resolve().parent / "fixtures" / "file_compare_llm"


@pytest.fixture
def profile():
    from lib.file_compare_llm.normalize import default_profile_path, load_profile

    return load_profile(default_profile_path())


def test_evidence_duplicate_and_drift(profile):
    from lib.file_compare_llm.evidence import build_evidence
    from lib.file_compare_llm.normalize import normalize_file

    fa = normalize_file(FIX / "fragments_dup_drift.json", profile)
    fb = normalize_file(FIX / "fragments_wrapped_broken_ref.json", profile)
    ev = build_evidence(profile, fa, fb)
    assert ev["file_a"]["duplicate_entity_ids"].get("issue/housing") == 2
    drift = ev["file_a"]["lexical_drift_flags"]
    subs = {d["substring"].lower() for d in drift}
    assert "github.com" in subs or "jira" in subs


def test_evidence_broken_sibling_reference(profile):
    from lib.file_compare_llm.evidence import build_evidence
    from lib.file_compare_llm.normalize import normalize_file

    fa = normalize_file(FIX / "fragments_dup_drift.json", profile)
    fb = normalize_file(FIX / "fragments_wrapped_broken_ref.json", profile)
    ev = build_evidence(profile, fa, fb)
    br = ev["file_b"]["broken_references"]
    assert any(r.get("value") == "issue/does_not_exist" for r in br)


def test_evidence_malformed_candidates(profile):
    from lib.file_compare_llm.evidence import build_evidence
    from lib.file_compare_llm.normalize import normalize_file

    fa = normalize_file(FIX / "malformed_ids.json", profile)
    fb = normalize_file(FIX / "fragments_wrapped_broken_ref.json", profile)
    ev = build_evidence(profile, fa, fb)
    mal = ev["file_a"]["malformed_entity_id_candidates"]
    assert "!!!bad-id" in mal
    assert any("other_unspecified" in m for m in mal)
