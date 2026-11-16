"""Stable ``studio_task_id`` values and labels for Lenses Studio AI routing (API + UI)."""

from __future__ import annotations

from typing import Final

# (studio_task_id, user-facing label) — order matches AI Setup routing preview table.
STUDIO_TASK_DEFINITIONS: Final[tuple[tuple[str, str], ...]] = (
    ("chat_assistant", "Chat assistant"),
    ("search_knowledge", "Search / knowledge answers"),
    ("plans_generation", "Plans / roadmaps generation"),
    ("site_drafting", "Site / blog drafting"),
    ("code_automation", "Code / automation"),
    ("extraction_classification", "Extraction / classification"),
    ("vision_ocr", "Vision / OCR"),
    ("embeddings_indexing", "Embeddings / indexing"),
    ("docs_health_enricher", "Docs Health — finding enricher"),
    ("docs_health_cluster", "Docs Health — cluster narrative"),
    ("docs_health_writer", "Docs Health — docs writer"),
    ("docs_health_diagram", "Docs Health — diagram draft"),
    ("docs_health_decision", "Docs Health — ADR / decision stub"),
    ("docs_health_reviewer", "Docs Health — reviewer"),
)

STUDIO_TASK_IDS: Final[frozenset[str]] = frozenset(t[0] for t in STUDIO_TASK_DEFINITIONS)
