"""Structured story definition from WBS rows, milestone prose, and roadmap sections."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote

from lenses.roadmap_outline import parse_roadmap_markdown
from lenses.safe_forge_paths import workspace_md_view_link
from lenses.wbs_model import WbsModel, WbsStory, WbsTask

# Story id token (not task)
_STORY_ID_RE = re.compile(r"^M\d+E\d+S\d+$")

# Columns to skip (handled elsewhere or not prose)
_SKIP_HEADERS = frozenset(
    {
        "story id",
        "id",
        "title",
        "story",
        "story title",
        "priority",
        "prio",
    }
)


def _norm(h: str) -> str:
    return re.sub(r"\s+", " ", (h or "").strip().lower())


def _slot_for_header(header: str) -> str | None:
    """Map a WBS table column header to a semantic slot, or None to skip / freeform."""
    h = _norm(header)
    if not h or h in _SKIP_HEADERS:
        return None
    if "story id" in h or h == "id":
        return None
    if h in ("title", "story title", "task title", "task"):
        return None
    if "acceptance" in h and "route" in h:
        return "acceptance_route"
    if "acceptance" in h or "criteria" in h or h in ("ac", "done when"):
        return "acceptance"
    if "problem" in h or "issue" in h:
        return "problem"
    if "rationale" in h or "why" in h or "motivation" in h:
        return "rationale"
    if "outcome" in h or "user visible" in h or "user-facing" in h or h == "value":
        return "user_visible_outcome"
    if "depend" in h or "deps" in h:
        return "dependencies"
    if "constraint" in h or "assumption" in h:
        return "constraints"
    if "blocker" in h:
        return "blockers"
    if "evidence" in h or "definition of done" in h or h in ("dod", "done"):
        return "evidence_of_done"
    if "phase" in h:
        return "phase"
    if "note" in h or "comment" in h or "detail" in h or "description" in h:
        return "notes_unstructured"
    return "notes_unstructured"


def _milestone_key_from_story_id(story_id: str) -> str | None:
    m = re.match(r"^(M\d+)", story_id.strip())
    return m.group(1) if m else None


def _excerpt(text: str, limit: int = 480) -> str:
    t = (text or "").strip()
    if len(t) <= limit:
        return t
    return t[: limit - 1].rstrip() + "…"


def roadmap_hits_for_story(
    roadmap_rel: str,
    roadmap_md: str,
    story_id: str,
) -> list[dict[str, Any]]:
    """Sections whose title or body mentions the story id."""
    if not _STORY_ID_RE.match(story_id.strip()):
        return []
    parsed = parse_roadmap_markdown(roadmap_md)
    token = story_id.strip()
    out: list[dict[str, Any]] = []
    for sec in parsed.sections:
        blob = f"{sec.title}\n{sec.body}"
        if token not in blob:
            continue
        rp = roadmap_rel.replace("\\", "/").strip("/")
        preview_href = (
            f"/roadmaps/preview?p={quote(rp)}&section={quote(sec.id)}"
        )
        out.append(
            {
                "section_id": sec.id,
                "title": sec.title,
                "excerpt": _excerpt(sec.body or sec.title),
                "preview_href": preview_href,
            }
        )
    return out


def synthesize_wbs_slots(
    story: WbsStory,
    wbs_rel: str,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """
    Map story.row cells to semantic slots. Multiple columns may merge into same slot (last wins)
    or we concatenate — we concatenate with '\\n\\n' for same slot from multiple columns.
    """
    wbs_href = f"/wbs/view?p={wbs_rel.replace(chr(92), '/')}"
    slots: dict[str, dict[str, Any]] = {}
    provenance: list[dict[str, Any]] = []

    row = story.row or {}
    for header, cell in row.items():
        text = (cell or "").strip()
        if not text:
            continue
        slot = _slot_for_header(header)
        if slot is None:
            continue
        entry = slots.setdefault(slot, {"text": "", "sources": []})
        if entry["text"]:
            entry["text"] += "\n\n" + text
        else:
            entry["text"] = text
        prov = {
            "slot": slot,
            "source": "wbs_column",
            "header": header,
            "href": wbs_href,
        }
        entry["sources"].append(prov)
        provenance.append(prov)

    # First-class fields from WbsStory (may duplicate row — prefer explicit story fields)
    if story.acceptance_summary and "acceptance" not in slots:
        slots["acceptance"] = {
            "text": story.acceptance_summary,
            "sources": [
                {
                    "slot": "acceptance",
                    "source": "wbs_acceptance_column",
                    "header": "acceptance",
                    "href": wbs_href,
                }
            ],
        }
    if story.dependencies:
        dep_text = ", ".join(story.dependencies)
        if "dependencies" in slots:
            slots["dependencies"]["text"] = (
                slots["dependencies"]["text"] + "\n\n" + dep_text
                if slots["dependencies"]["text"]
                else dep_text
            )
        else:
            slots["dependencies"] = {
                "text": dep_text,
                "sources": [
                    {
                        "slot": "dependencies",
                        "source": "wbs_dependencies_column",
                        "header": "dependencies",
                        "href": wbs_href,
                    }
                ],
            }

    return slots, provenance


def milestone_outcome_block(
    model: WbsModel,
    story_id: str,
    wbs_rel: str,
) -> dict[str, Any] | None:
    mk = _milestone_key_from_story_id(story_id)
    if not mk:
        return None
    prose = (model.milestone_outcomes or {}).get(mk, "").strip()
    if not prose:
        return None
    return {
        "text": prose,
        "milestone_id": mk,
        "sources": [
            {
                "slot": "milestone_context",
                "source": "wbs_milestone_prose",
                "header": f"Milestone {mk}",
                "href": f"/wbs/view?p={wbs_rel.replace(chr(92), '/')}",
            }
        ],
    }


def phase_affinity_from_tasks(tasks: list[WbsTask]) -> list[str]:
    phases: list[str] = []
    seen: set[str] = set()
    for t in tasks:
        row = t.row or {}
        for key, val in row.items():
            if _norm(key) == "phase" or "phase" in _norm(key):
                p = (val or "").strip()
                if p and p not in seen:
                    seen.add(p)
                    phases.append(p)
                break
    return phases


def build_story_view_dict(
    story: WbsStory,
    model: WbsModel,
    wbs_rel: str,
    roadmap_rel: str | None,
    roadmap_md: str | None,
    *,
    work_item_id: str,
) -> dict[str, Any]:
    """Assemble story_view for API JSON (story-level; spark uses parent story)."""
    slots, _prov_list = synthesize_wbs_slots(story, wbs_rel)
    milestone_ctx = milestone_outcome_block(model, story.id, wbs_rel)

    user_outcome = (slots.get("user_visible_outcome") or {}).get("text", "").strip()
    merged_milestone = False
    if milestone_ctx and not user_outcome:
        slots["user_visible_outcome"] = {
            "text": milestone_ctx["text"],
            "sources": milestone_ctx["sources"],
            "inherited_from_milestone": True,
        }
        merged_milestone = True

    roadmap_hits: list[dict[str, Any]] = []
    if roadmap_rel and roadmap_md:
        roadmap_hits = roadmap_hits_for_story(roadmap_rel, roadmap_md, story.id)

    phases = phase_affinity_from_tasks(story.tasks)

    return {
        "work_item_id": work_item_id,
        "story_id": story.id,
        "slots": {k: v for k, v in slots.items()},
        "milestone_outcome": None if merged_milestone else milestone_ctx,
        "phase_affinity": phases,
        "roadmap_hits": roadmap_hits,
    }
