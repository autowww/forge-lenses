"""Deterministic interpretation output for tests and local dev."""

from __future__ import annotations

from typing import Any

from lenses.blueprints_wizard.interpretation_normalize import normalize_interpretation_payload


def mock_interpretation_raw() -> dict[str, Any]:
    """LLM-shaped dict before ``normalize_interpretation_payload``."""
    return {
        "what_user_said": (
            "[mock] Mission and context indicate a need to align stakeholders on delivery scope "
            "and reduce onboarding friction."
        ),
        "inferred": [
            {
                "id": "mock-inf-1",
                "text": "Primary pain is unclear ownership between product and platform teams.",
                "status": "inferred",
                "confidence": 0.62,
            },
            {
                "id": "mock-inf-2",
                "text": "Success likely measured by time-to-first-value and support ticket volume.",
                "status": "inferred",
                "confidence": 0.55,
            },
        ],
        "needs_confirmation": [
            {
                "id": "mock-nc-1",
                "text": "Whether regulatory review is required before launch.",
                "status": "needs_confirmation",
                "confidence": 0.4,
            },
        ],
        "unknowns": [
            "Integration timeline with the legacy auth system.",
            "Budget ceiling for external vendors.",
        ],
        "foundation_brief_draft": {
            "problem_statement": {
                "text": "Teams lack a shared picture of scope and constraints, slowing decisions.",
                "status": "inferred",
                "confidence": 0.58,
            },
            "desired_outcome": {
                "text": "A documented Foundation Brief and agreed success metrics.",
                "status": "inferred",
                "confidence": 0.5,
            },
            "target_users_stakeholders": {
                "text": "Product owners, engineering leads, and customer success.",
                "status": "unknown",
            },
            "scope": {
                "text": "Wizard-led intake through understanding; no automated downstream generation.",
                "status": "explicit",
                "confidence": 0.9,
            },
            "non_goals": {
                "text": "Full solution architecture and implementation planning.",
                "status": "inferred",
                "confidence": 0.45,
            },
            "success_metrics": {
                "text": "TBD — confirm with stakeholders.",
                "status": "needs_confirmation",
                "confidence": 0.3,
            },
            "constraints": {
                "text": "Experimental Blueprints Wizard feature flag; loopback LLM only in default setup.",
                "status": "explicit",
                "confidence": 0.85,
            },
            "assumptions": {
                "text": "Repository context and notes are representative of intent.",
                "status": "inferred",
                "confidence": 0.5,
            },
            "dependencies": {
                "text": "Forge Blueprints handbook alignment.",
                "status": "unknown",
            },
            "risks": {
                "text": "Incomplete context may skew inferred items.",
                "status": "inferred",
                "confidence": 0.6,
            },
            "open_questions": {
                "text": "Who signs off on scope? What is the launch window?",
                "status": "needs_confirmation",
                "confidence": 0.35,
            },
            "glossary_key_terms": {
                "text": "Foundation Brief: structured problem/outcome/scope snapshot.",
                "status": "explicit",
                "confidence": 0.7,
            },
        },
    }


def mock_interpretation_normalized() -> dict[str, Any]:
    return normalize_interpretation_payload(mock_interpretation_raw())
