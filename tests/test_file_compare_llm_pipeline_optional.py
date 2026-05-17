"""Optional live LLM test for file compare (skipped without LLM_BASE_URL)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytest.importorskip("yaml")

from lib.file_compare_llm.evidence import build_evidence
from lib.file_compare_llm.llm_pipeline import run_llm_pipeline
from lib.file_compare_llm.normalize import load_profile, normalize_file


ROOT = Path(__file__).resolve().parents[1]
FX = ROOT / "tests/fixtures/file_compare_llm"


@pytest.mark.skipif(
    not os.environ.get("LLM_BASE_URL", "").strip(),
    reason="Set LLM_BASE_URL to run live file-compare LLM pipeline test",
)
def test_run_llm_pipeline_on_fixtures() -> None:
    profile = load_profile(None)
    fa = normalize_file(FX / "fragments_dup_drift.json", profile)
    fb = normalize_file(FX / "fragments_wrapped_broken_ref.json", profile)
    ev = build_evidence(profile, fa, fb)
    merged, dbg = run_llm_pipeline(
        profile=profile,
        evidence=ev,
        fa=fa,
        fb=fb,
        model=os.environ.get("LLM_MODEL") or None,
        temperature=0.2,
        excerpt_cap=8000,
        debug=False,
    )
    assert "pass2" in merged and isinstance(merged["pass2"], dict)
    assert "pass3" in merged and isinstance(merged["pass3"], dict)
    assert isinstance(dbg, dict)
