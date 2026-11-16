"""Optional prompt materialization for Cursor Launch Pack (experimental)."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class PromptMaterializer(Protocol):
    """Fill prompt bodies for ``build_time_dynamic`` recipes; production may swap in LLM-backed impl."""

    def materialize_placeholder(self, recipe: dict[str, Any]) -> str:
        """Return markdown or plain text to embed when final prompt is not yet rendered."""
        ...


class NullPromptMaterializer:
    """Deterministic placeholder text; no network or LLM."""

    def materialize_placeholder(self, recipe: dict[str, Any]) -> str:
        rid = str(recipe.get("recipe_id") or "").strip() or "(no recipe_id)"
        summary = str(recipe.get("placeholder_summary") or "").strip()
        inputs = recipe.get("materialization_inputs")
        lines = [
            "# Prompt placeholder (build-time dynamic)",
            "",
            f"Recipe: `{rid}`",
            "",
        ]
        if summary:
            lines.append(summary)
            lines.append("")
        if isinstance(inputs, list) and inputs:
            lines.append("Expected inputs:")
            for x in inputs[:32]:
                if isinstance(x, str) and x.strip():
                    lines.append(f"- {x.strip()}")
            lines.append("")
        lines.append("_Materialize this prompt in Cursor using session context and nodes/ artifacts._")
        return "\n".join(lines)
