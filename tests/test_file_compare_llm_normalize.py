from __future__ import annotations

from pathlib import Path

import pytest

FIX = Path(__file__).resolve().parent / "fixtures" / "file_compare_llm"


@pytest.fixture
def profile():
    from lib.file_compare_llm.normalize import default_profile_path, load_profile

    return load_profile(default_profile_path())


def test_normalize_json_unwraps_target_node(profile):
    from lib.file_compare_llm.normalize import normalize_file

    p = FIX / "fragments_wrapped_broken_ref.json"
    fp = normalize_file(p, profile)
    assert fp.parse_ok
    assert fp.structured_records is not None
    assert len(fp.structured_records) == 1
    assert fp.structured_records[0].get("taxonomy_id") == "issue/mental_health"
    assert any("Unwrapped" in w for w in fp.normalization_warnings)


def test_normalize_duplicate_entities(profile):
    from lib.file_compare_llm.normalize import normalize_file

    p = FIX / "fragments_dup_drift.json"
    fp = normalize_file(p, profile)
    assert fp.entity_candidates.count("issue/housing") == 2


def test_normalize_plaintext(profile):
    from lib.file_compare_llm.normalize import normalize_file

    p = FIX / "plain_notes.txt"
    fp = normalize_file(p, profile)
    assert fp.file_type in ("plaintext", "unknown")
    assert fp.section_candidates[0].startswith("chunk:0")


def test_normalize_malformed_ids(profile):
    from lib.file_compare_llm.normalize import normalize_file

    p = FIX / "malformed_ids.json"
    fp = normalize_file(p, profile)
    assert "!!!bad-id" in fp.entity_candidates
