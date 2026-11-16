"""Fleet settings v2 (multi-node) persistence."""

from __future__ import annotations

import json
from pathlib import Path

from lenses.fleet_settings_store import load_raw, merge_save, save_raw, sanitize_for_get


def test_migrate_v1_to_nodes(tmp_path: Path) -> None:
    p = tmp_path / ".lenses-local" / "fleet-settings.json"
    p.parent.mkdir(parents=True)
    p.write_text(
        json.dumps({"version": 1, "base_url": "http://127.0.0.1:18765", "bearer_token": "secret"}),
        encoding="utf-8",
    )
    data = load_raw(tmp_path)
    assert data["version"] == 2
    assert len(data["nodes"]) == 1
    assert data["nodes"][0]["base_url"] == "http://127.0.0.1:18765"
    assert data["nodes"][0]["bearer_token"] == "secret"


def test_merge_nodes_preserves_token_when_key_omitted(tmp_path: Path) -> None:
    save_raw(
        tmp_path,
        {
            "version": 2,
            "nodes": [
                {
                    "id": "a",
                    "base_url": "http://h1",
                    "bearer_token": "tok1",
                    "enabled": True,
                    "priority": 5,
                    "max_cpu_percent": None,
                    "max_memory_percent": None,
                }
            ],
        },
    )
    merged = merge_save(
        tmp_path,
        {
            "nodes": [
                {
                    "id": "a",
                    "base_url": "http://h2",
                    "enabled": True,
                    "priority": 3,
                }
            ]
        },
    )
    assert merged["nodes"][0]["base_url"] == "http://h2"
    assert merged["nodes"][0]["bearer_token"] == "tok1"
    assert merged["nodes"][0]["priority"] == 3


def test_sanitize_masks_token(tmp_path: Path) -> None:
    raw = load_raw(tmp_path)
    raw["nodes"] = [
        {
            "id": "x",
            "base_url": "http://127.0.0.1:1",
            "bearer_token": "abcdefghijklmnop",
            "enabled": True,
            "priority": 1,
            "max_cpu_percent": 90.0,
            "max_memory_percent": 85.0,
        }
    ]
    s = sanitize_for_get(raw)
    assert s["nodes"][0]["bearer_token_configured"] is True
    assert s["nodes"][0]["bearer_token"] != "abcdefghijklmnop"
