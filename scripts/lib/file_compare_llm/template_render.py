from __future__ import annotations

from pathlib import Path

_TEMPLATES_DIR = Path(__file__).resolve().parent / "prompt_templates"


def render_template(filename: str, replacements: dict[str, str]) -> str:
    path = _TEMPLATES_DIR / filename
    text = path.read_text(encoding="utf-8")
    for key, val in replacements.items():
        text = text.replace(key, val)
    return text


def load_system_prompt() -> str:
    return (_TEMPLATES_DIR / "system.md").read_text(encoding="utf-8")
