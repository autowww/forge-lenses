"""Turn reflection heuristics (no LLM)."""

from __future__ import annotations

from lenses.sdlc_copilot.turn_reflection import build_turn_reflection


def test_reflection_hedged_no_citations() -> None:
    r = build_turn_reflection(
        user_message="Are we in threads mode?",
        assistant_text="I don't have enough evidence from these sources alone to confirm.",
        citation_count=0,
        grounding_truncated=False,
    )
    assert r.get("answered") in ("no", "partial")
    assert r.get("adjust_context") is True
    assert "hedges" in (r.get("agent_note") or "").lower() or "sources" in (r.get("agent_note") or "").lower()


def test_reflection_grounded_yes() -> None:
    r = build_turn_reflection(
        user_message="What is in charge.md?",
        assistant_text="The file describes the charge model [1].",
        citation_count=3,
        grounding_truncated=False,
    )
    assert r.get("answered") == "yes"
    assert r.get("adjust_context") is False
    c = r.get("confidence")
    assert isinstance(c, (int, float))
    assert 0.5 <= float(c) <= 0.95


def test_grounded_yes_confidence_varies_with_answer_length() -> None:
    """Same citation count; longer assistant reply nudges heuristic confidence (bounded)."""
    short = build_turn_reflection(
        user_message="q",
        assistant_text="Brief [1].",
        citation_count=5,
        grounding_truncated=False,
    )
    long = build_turn_reflection(
        user_message="q",
        assistant_text=("Paragraph [1]. " * 200).strip(),
        citation_count=5,
        grounding_truncated=False,
    )
    assert short.get("answered") == "yes" and long.get("answered") == "yes"
    assert float(short["confidence"]) < float(long["confidence"])  # type: ignore[index]


def test_grounded_yes_confidence_varies_with_citation_kind_diversity() -> None:
    """Same citation count; more distinct citation kinds increases diversity term."""
    mono_kind = [
        {"kind": "fts", "id": i + 1, "title": "t", "ref": "", "snippet": "s"}
        for i in range(4)
    ]
    mixed_kind = [
        {"kind": "a", "id": 1, "title": "t", "ref": "", "snippet": "s"},
        {"kind": "b", "id": 2, "title": "t", "ref": "", "snippet": "s"},
        {"kind": "c", "id": 3, "title": "t", "ref": "", "snippet": "s"},
        {"kind": "d", "id": 4, "title": "t", "ref": "", "snippet": "s"},
    ]
    r_mono = build_turn_reflection(
        user_message="q",
        assistant_text="Answer with citations [1][2][3][4].",
        citation_count=4,
        grounding_truncated=False,
        citations=mono_kind,
    )
    r_mix = build_turn_reflection(
        user_message="q",
        assistant_text="Answer with citations [1][2][3][4].",
        citation_count=4,
        grounding_truncated=False,
        citations=mixed_kind,
    )
    assert r_mono.get("answered") == "yes" and r_mix.get("answered") == "yes"
    assert float(r_mono["confidence"]) < float(r_mix["confidence"])  # type: ignore[index]


def test_satisfaction_low_when_assistant_deflects_with_citations() -> None:
    """Deflection despite grounded context → partial + low satisfaction (confidence tag)."""
    assistant = (
        "I'm unable to assist with adding sticky notes as the context provided is focused on Forge Studio, "
        "which includes topics like studio pages and handoff targets. None of these items pertain to adding "
        "sticky notes in a general sense. Apologies for any inconvenience!"
    )
    r = build_turn_reflection(
        user_message="let's add some sticky notes here",
        assistant_text=assistant,
        citation_count=7,
        grounding_truncated=False,
    )
    assert r.get("answered") == "partial"
    assert float(r["confidence"]) < 0.45  # type: ignore[index]
    assert r.get("adjust_context") is True
    assert r.get("confidence_semantic") == "satisfaction"


def test_satisfaction_helpful_still_yes_with_semantic_tag() -> None:
    r = build_turn_reflection(
        user_message="What is in charge.md?",
        assistant_text="The file describes the charge model [1] with details from the workspace.",
        citation_count=3,
        grounding_truncated=False,
    )
    assert r.get("answered") == "yes"
    assert r.get("confidence_semantic") == "satisfaction"


def test_context_gap_whether_is_partial_not_yes() -> None:
    """Polite 'context does not say whether…' answers must not score like a fulfilled request."""
    assistant = (
        "Based on the workspace materials, the provided context does not contain any information "
        "about whether you can place a sticky note in this part of the interface. "
        "If you describe the surface (desk vs wall), I can narrow the search."
    )
    r = build_turn_reflection(
        user_message="can I put a sticky note here?",
        assistant_text=assistant,
        citation_count=6,
        grounding_truncated=False,
    )
    assert r.get("answered") == "partial"
    assert float(r["confidence"]) < 0.45  # type: ignore[index]
    assert r.get("adjust_context") is True


def test_hedged_with_citations_lowers_confidence() -> None:
    r = build_turn_reflection(
        user_message="Is feature X enabled?",
        assistant_text=(
            "I don't have enough evidence from these sources alone to confirm whether feature X is on. "
            "See [1] for related configuration notes."
        ),
        citation_count=4,
        grounding_truncated=False,
    )
    assert r.get("answered") == "partial"
    assert float(r["confidence"]) < 0.42  # type: ignore[index]
