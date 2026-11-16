"""Versioned bridge registry: lifecycle, ceremonies, terminology, OGS→canonical map."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BridgeRegistry:
    """Loaded ``registry.v1.json`` with lookup helpers."""

    raw: dict[str, Any]

    @property
    def schema_version(self) -> str:
        return str(self.raw.get("schema_version") or "")

    @property
    def registry_version(self) -> str:
        return str(self.raw.get("registry_version") or "")

    def public_payload(self) -> dict[str, Any]:
        """Safe for GET /api/bridge/registry (full reference; no secrets)."""
        return self.raw

    def ogs_kind_to_canonical(self, ogs_kind: str) -> str:
        m = self.raw.get("ogs_kind_to_canonical")
        if isinstance(m, dict) and ogs_kind in m:
            return str(m[ogs_kind])
        return "work_unit"

    def lookup_neutral_term(self, term: str) -> dict[str, Any] | None:
        t = term.strip().lower()
        for row in self.raw.get("terminology") or []:
            if not isinstance(row, dict):
                continue
            neutral = str(row.get("neutral") or "").strip().lower()
            if neutral == t:
                return row
            for lab in (
                row.get("forge_labels") or [],
                row.get("sdlc_labels") or [],
                row.get("pdlc_labels") or [],
            ):
                if not isinstance(lab, list):
                    continue
                for x in lab:
                    if str(x).strip().lower() == t:
                        return row
        return None

    def reverse_lookup_labels(self, label_fragment: str) -> list[dict[str, Any]]:
        frag = label_fragment.strip().lower()
        out: list[dict[str, Any]] = []
        for row in self.raw.get("terminology") or []:
            if not isinstance(row, dict):
                continue
            neutral = str(row.get("neutral") or "")
            hits: list[str] = []
            for key in ("forge_labels", "sdlc_labels", "pdlc_labels"):
                for x in row.get(key) or []:
                    if frag in str(x).lower():
                        hits.append(str(x))
            if frag in neutral.lower() or hits:
                out.append({"neutral": neutral, "matched_labels": hits, "entry": row})
        return out

    def term_collisions(self) -> list[dict[str, Any]]:
        tc = self.raw.get("term_collisions")
        return [x for x in tc if isinstance(x, dict)] if isinstance(tc, list) else []

    def trace_rules(self, canonical_kind: str) -> dict[str, list[str]]:
        rules = self.raw.get("canonical_trace_rules")
        if not isinstance(rules, dict):
            return {"recommended_in": [], "recommended_out": []}
        row = rules.get(canonical_kind)
        if not isinstance(row, dict):
            return {"recommended_in": [], "recommended_out": []}
        ri = row.get("recommended_in") or []
        ro = row.get("recommended_out") or []
        return {
            "recommended_in": [str(x) for x in ri if x],
            "recommended_out": [str(x) for x in ro if x],
        }


def _registry_path() -> Path:
    return Path(__file__).resolve().parent / "data" / "registry.v1.json"


@lru_cache(maxsize=1)
def load_bridge_registry() -> BridgeRegistry:
    path = _registry_path()
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("bridge registry must be a JSON object")
    return BridgeRegistry(raw=data)


def validate_registry_struct(reg: BridgeRegistry) -> list[str]:
    """Return human-readable issues (empty if OK)."""
    issues: list[str] = []
    if not reg.schema_version:
        issues.append("missing schema_version")
    if not reg.registry_version:
        issues.append("missing registry_version")
    og = reg.raw.get("ogs_kind_to_canonical")
    if not isinstance(og, dict) or not og:
        issues.append("ogs_kind_to_canonical must be a non-empty object")
    seen_neutral: set[str] = set()
    for row in reg.raw.get("terminology") or []:
        if not isinstance(row, dict):
            continue
        n = str(row.get("neutral") or "").strip()
        if not n:
            issues.append("terminology row missing neutral")
            continue
        if n in seen_neutral:
            issues.append(f"duplicate neutral term: {n}")
        seen_neutral.add(n)
    return issues
