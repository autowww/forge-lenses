"""custom_provider merge in llm_settings_store."""

from __future__ import annotations

from pathlib import Path

from lenses.llm_settings_store import load_raw, merge_save, save_raw


def test_merge_save_custom_provider(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    save_raw(root, load_raw(root))
    merged = merge_save(
        root,
        {
            "custom_provider": {
                "display_name": "LM Studio",
                "transport": "openai_compatible",
                "auth": "none",
            }
        },
    )
    save_raw(root, merged)
    data = load_raw(root)
    cp = data.get("custom_provider")
    assert isinstance(cp, dict)
    assert cp.get("display_name") == "LM Studio"
    assert cp.get("auth") == "none"
