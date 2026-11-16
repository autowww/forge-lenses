"""Validate handbook JSON schemas and paired examples."""

from __future__ import annotations

import json
from pathlib import Path

import referencing
from jsonschema import Draft202012Validator
from referencing.jsonschema import DRAFT202012

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = ROOT / "docs" / "schemas"
EXAMPLE_DIR = ROOT / "docs" / "examples"


def _schema_registry() -> tuple[dict[str, dict], referencing.Registry]:
    by_id: dict[str, dict] = {}
    for path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        sid = data.get("$id")
        assert sid, f"$id missing: {path}"
        by_id[sid] = data

    registry: referencing.Registry = referencing.Registry()
    for sid, data in by_id.items():
        registry = registry.with_resource(sid, DRAFT202012.create_resource(data))
    return by_id, registry


def test_every_schema_registers_and_meta_validates():
    by_id, registry = _schema_registry()
    for sid, schema in by_id.items():
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema, registry=registry)


def test_examples_match_contracts():
    by_id, registry = _schema_registry()
    paired = 0
    for schema_path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        stem = schema_path.name[: -len(".schema.json")]
        sample_path = EXAMPLE_DIR / f"sample-{stem}.json"
        assert sample_path.is_file(), f"missing sample for {schema_path.name} ({sample_path.name})"
        data = json.loads(schema_path.read_text(encoding="utf-8"))
        sid = data.get("$id")
        assert sid and sid in by_id, f"invalid $id for {schema_path.name}: {sid!r}"
        schema = by_id[str(sid)]
        instance = json.loads(sample_path.read_text(encoding="utf-8"))
        Draft202012Validator(schema, registry=registry).validate(instance)
        paired += 1

    assert paired >= 14, f"need at least 14 schema/example pairs for docs tooling, saw {paired}"

