"""
Deterministic evidence only (clues for LLM). Does not assign semantic winners.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from difflib import SequenceMatcher
from typing import Any

from .normalize import FileProfile


def _jaccard(a: list[str], b: list[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    u = len(sa | sb)
    return len(sa & sb) / u if u else 0.0


def _malformed_ids(ids: list[str], patterns: list[str]) -> list[str]:
    out: list[str] = []
    for i in ids:
        for pid in patterns:
            try:
                if re.fullmatch(pid, i) or re.search(pid, i):
                    if i not in out:
                        out.append(i)
                    break
            except re.error:
                if pid.lower() in i.lower():
                    if i not in out:
                        out.append(i)
                    break
    return out


def _duplicate_ids(ids: list[str]) -> dict[str, int]:
    c = Counter(ids)
    return {k: v for k, v in c.items() if v > 1}


def _lexical_drift_flags(
    records: list[dict[str, Any]] | None,
    substrings: list[str],
    case_insensitive: bool,
    max_flags: int | None = None,
    snippet_max_chars: int | None = None,
) -> list[dict[str, Any]]:
    """max_flags None or <=0 means no cap. snippet_max_chars None or <=0 means full record JSON per flag."""
    if not records or not substrings:
        return []
    flags: list[dict[str, Any]] = []
    for idx, rec in enumerate(records):
        try:
            blob = json.dumps(rec, ensure_ascii=False)
        except TypeError:
            blob = str(rec)
        hay = blob.lower() if case_insensitive else blob
        for sub in substrings:
            s = sub.lower() if case_insensitive else sub
            if s in hay:
                snip = blob.replace("\n", " ")
                if snippet_max_chars is not None and snippet_max_chars > 0:
                    snip = snip[:snippet_max_chars]
                flags.append(
                    {
                        "record_index": idx,
                        "substring": sub,
                        "snippet": snip,
                    }
                )
                if max_flags is not None and max_flags > 0 and len(flags) >= max_flags:
                    return flags
    return flags


def _broken_refs(
    records: list[dict[str, Any]],
    checks: list[dict[str, Any]],
    id_universe: set[str],
) -> list[dict[str, Any]]:
    broken: list[dict[str, Any]] = []
    for rec_idx, rec in enumerate(records):
        for chk in checks:
            if not isinstance(chk, dict):
                continue
            field = chk.get("field")
            list_under = chk.get("list_under")
            nested_id = chk.get("nested_id_field")
            if list_under and nested_id:
                inner = rec.get(list_under)
                if isinstance(inner, list):
                    for j, item in enumerate(inner):
                        if isinstance(item, dict):
                            sid = item.get(nested_id)
                            if isinstance(sid, str) and sid and sid not in id_universe:
                                broken.append(
                                    {
                                        "record_index": rec_idx,
                                        "field": f"{list_under}[{j}].{nested_id}",
                                        "value": sid,
                                        "reason": "not_in_universe",
                                    }
                                )
                continue
            if not field:
                continue
            val = rec.get(field)
            if isinstance(val, str) and val and val not in id_universe:
                broken.append(
                    {
                        "record_index": rec_idx,
                        "field": field,
                        "value": val,
                        "reason": "not_in_universe",
                    }
                )
    return broken


def build_evidence(profile: dict[str, Any], fa: FileProfile, fb: FileProfile) -> dict[str, Any]:
    ev_cfg = profile.get("evidence") or {}
    id_fields: list[str] = list(ev_cfg.get("entity_id_fields") or ["taxonomy_id", "id"])
    mal_patterns = list(ev_cfg.get("malformed_id_patterns") or [])
    drift_cfg = ev_cfg.get("lexical_drift") or {}
    drift_subs = list(drift_cfg.get("suspicious_substrings") or [])
    ci = bool(drift_cfg.get("case_insensitive", True))
    max_drift = drift_cfg.get("max_flags")
    if isinstance(max_drift, int):
        max_drift_i: int | None = max_drift
    elif isinstance(max_drift, str) and max_drift.strip().isdigit():
        max_drift_i = int(max_drift)
    else:
        max_drift_i = None
    if max_drift_i is not None and max_drift_i <= 0:
        max_drift_i = None
    snip_cap = drift_cfg.get("snippet_max_chars")
    try:
        snip_n = int(snip_cap) if snip_cap is not None else None
    except (TypeError, ValueError):
        snip_n = None
    if snip_n is not None and snip_n <= 0:
        snip_n = None
    key_hist_cap = ev_cfg.get("max_key_shape_histogram")
    try:
        key_hist_n = int(key_hist_cap) if key_hist_cap is not None else None
    except (TypeError, ValueError):
        key_hist_n = None
    if key_hist_n is not None and key_hist_n <= 0:
        key_hist_n = None
    diff_cap = ev_cfg.get("max_entity_id_diff_list")
    try:
        diff_n = int(diff_cap) if diff_cap is not None else None
    except (TypeError, ValueError):
        diff_n = None
    if diff_n is not None and diff_n <= 0:
        diff_n = None

    def per_file(fp: FileProfile, label: str) -> dict[str, Any]:
        ids = list(fp.entity_candidates)
        dup = _duplicate_ids(ids)
        mal_set = _malformed_ids(ids, mal_patterns) if mal_patterns else []
        recs = fp.structured_records or []
        key_shapes: dict[str, int] = {}
        for rec in recs:
            for k in rec.keys():
                key_shapes[k] = key_shapes.get(k, 0) + 1
        drift = _lexical_drift_flags(recs, drift_subs, ci, max_flags=max_drift_i, snippet_max_chars=snip_n)
        lines = fp.raw_text.splitlines()
        lens = [len(x) for x in lines] if lines else [0]
        sorted_shapes = sorted(key_shapes.items(), key=lambda x: -x[1])
        if key_hist_n is not None and key_hist_n > 0:
            sorted_shapes = sorted_shapes[:key_hist_n]
        return {
            "label": label,
            "path": fp.path,
            "file_type": fp.file_type,
            "parse_ok": fp.parse_ok,
            "parse_errors": fp.parse_errors,
            "record_count": len(recs),
            "entity_id_count": len(ids),
            "unique_entity_ids": len(set(ids)),
            "duplicate_entity_ids": dup,
            "malformed_entity_id_candidates": mal_set,
            "key_shape_counts": dict(sorted_shapes),
            "normalization_warnings": fp.normalization_warnings,
            "schema_hint": fp.schema_hint,
            "line_count": len(lines),
            "max_line_length": max(lens) if lens else 0,
            "lexical_drift_flags": drift,
        }

    ua = set(fa.entity_candidates)
    ub = set(fb.entity_candidates)
    universe = ua | ub

    broken_a: list[dict[str, Any]] = []
    broken_b: list[dict[str, Any]] = []
    checks = ev_cfg.get("reference_checks") or []
    if isinstance(checks, list) and fa.structured_records:
        broken_a = _broken_refs(fa.structured_records, checks, universe)
    if isinstance(checks, list) and fb.structured_records:
        broken_b = _broken_refs(fb.structured_records, checks, universe)

    only_a = sorted(ua - ub)
    only_b = sorted(ub - ua)
    if diff_n is not None and diff_n > 0:
        only_a = only_a[:diff_n]
        only_b = only_b[:diff_n]
    pair = {
        "jaccard_entity_ids": round(_jaccard(fa.entity_candidates, fb.entity_candidates), 4),
        "entity_ids_only_in_a": only_a,
        "entity_ids_only_in_b": only_b,
        "similarity_ratio_lines": round(
            SequenceMatcher(a=fa.raw_text.splitlines(), b=fb.raw_text.splitlines()).ratio(),
            4,
        ),
    }

    return {
        "file_a": {**per_file(fa, "A"), "broken_references": broken_a},
        "file_b": {**per_file(fb, "B"), "broken_references": broken_b},
        "pairwise": pair,
    }
