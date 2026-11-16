"""
File normalization: type detection, parse, canonical records, section/entity candidates.
"""

from __future__ import annotations

import fnmatch
import json
import re
from copy import deepcopy
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Literal

_FILE_COMPARE_ROOT = Path(__file__).resolve().parent

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore

FileType = Literal["json", "yaml", "markdown", "plaintext", "code", "unknown"]


def default_profile_path() -> Path:
    return _FILE_COMPARE_ROOT / "compare_profile.yaml"


def load_profile(path: Path | None) -> dict[str, Any]:
    p = path or default_profile_path()
    raw = p.read_text(encoding="utf-8")
    if yaml is None:
        raise RuntimeError("PyYAML is required for compare_profile.yaml")
    data = yaml.safe_load(raw)
    return data if isinstance(data, dict) else {}


_MD_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)

# Reuse code extensions from deterministic without circular import at runtime
_CODE_EXT = frozenset(
    {
        ".py", ".pyi", ".rs", ".go", ".java", ".kt", ".kts", ".c", ".h", ".cpp", ".hpp",
        ".cc", ".cs", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".swift", ".rb",
        ".php", ".scala", ".sql", ".sh", ".bash", ".zsh",
    }
)


@dataclass
class FileProfile:
    path: str
    file_type: FileType
    raw_text: str
    byte_size: int
    sha256_hex: str
    parse_ok: bool
    parse_errors: list[str] = field(default_factory=list)
    structured_records: list[dict[str, Any]] | None = None
    section_candidates: list[str] = field(default_factory=list)
    entity_candidates: list[str] = field(default_factory=list)
    normalization_warnings: list[str] = field(default_factory=list)
    schema_hint: str = ""
    top_level_keys: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


def _detect_type(path: Path) -> FileType:
    suf = path.suffix.lower()
    if suf in (".json",):
        return "json"
    if suf in (".yaml", ".yml"):
        return "yaml"
    if suf in (".md", ".markdown"):
        return "markdown"
    if suf in (".txt",):
        return "plaintext"
    if suf in _CODE_EXT:
        return "code"
    return "unknown"


def _read_bytes(path: Path) -> tuple[bytes, str]:
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    import hashlib

    hx = hashlib.sha256(raw).hexdigest()
    return raw, hx


def _flatten_wrappers(obj: Any, rules: list[dict[str, Any]], warnings: list[str]) -> Any:
    if not isinstance(obj, dict) or not rules:
        return obj
    for rule in rules:
        path = rule.get("path") or ""
        inner = rule.get("inner_key") or ""
        if not path or not inner:
            continue
        cur = obj
        parts = path.split("/")
        for seg in parts[:-1]:
            if not isinstance(cur, dict) or seg not in cur:
                cur = None
                break
            cur = cur[seg]
        if cur is None:
            continue
        last = parts[-1]
        if not isinstance(cur, dict) or last not in cur:
            continue
        slot = cur[last]
        if not isinstance(slot, list):
            continue
        new_list: list[Any] = []
        changed = False
        for i, item in enumerate(slot):
            if isinstance(item, dict) and inner in item and isinstance(item[inner], dict):
                new_list.append(deepcopy(item[inner]))
                changed = True
                warnings.append(f"Unwrapped {path}[{i}].{inner} per profile.")
            elif isinstance(item, dict) and inner in item:
                new_list.append(item[inner])
                changed = True
                warnings.append(f"Unwrapped {path}[{i}].{inner} (non-dict) per profile.")
            else:
                new_list.append(item)
        if changed:
            cur[last] = new_list
    return obj


def _apply_key_aliases(rec: dict[str, Any], aliases: dict[str, str], warnings: list[str]) -> dict[str, Any]:
    if not aliases:
        return rec
    out = dict(rec)
    for old, new in aliases.items():
        if old in out and new not in out:
            out[new] = out.pop(old)
        elif old in out and new in out:
            warnings.append(f"Alias skip: both '{old}' and '{new}' present; keeping '{new}'.")
            del out[old]
    return out


def _extract_records(data: Any, warnings: list[str]) -> list[dict[str, Any]] | None:
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for key in ("fragments", "nodes", "items", "records"):
            if key in data and isinstance(data[key], list):
                lst = data[key]
                if all(isinstance(x, dict) for x in lst):
                    return list(lst)
                warnings.append(f"Key {key!r} is not a list of objects; skipping structured extraction.")
        return None
    return None


def _schema_hint(data: Any) -> str:
    if isinstance(data, dict):
        v = data.get("schema_version")
        if isinstance(v, str):
            return v
    return ""


def _required_fields_for(profile: dict, schema_hint: str, filename: str) -> list[str]:
    norm = profile.get("normalization") or {}
    reqs = norm.get("required_fields") or []
    out: list[str] = []
    for block in reqs:
        if not isinstance(block, dict):
            continue
        m = block.get("match") or "*"
        fields = block.get("fields") or []
        if not isinstance(fields, list):
            continue
        if m == "*" or (schema_hint and m in schema_hint) or fnmatch.fnmatch(filename, m):
            for f in fields:
                if isinstance(f, str):
                    out.append(f)
    # de-dupe preserve order
    seen: set[str] = set()
    uniq = []
    for f in out:
        if f not in seen:
            seen.add(f)
            uniq.append(f)
    return uniq


def _entity_ids_from_records(records: list[dict[str, Any]], fields: list[str]) -> list[str]:
    ids: list[str] = []
    for rec in records:
        for f in fields:
            v = rec.get(f)
            if isinstance(v, str) and v.strip():
                ids.append(v.strip())
                break
    return ids


def _markdown_sections(text: str) -> list[str]:
    return [m.group(2).strip() for m in _MD_HEADING.finditer(text)]


def _plaintext_chunks(text: str, max_chunks: int = 0) -> list[str]:
    """max_chunks <= 0 means all paragraphs; chunk ids are compact (indices only)."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if max_chunks and max_chunks > 0:
        paras = paras[:max_chunks]
    return [f"chunk:{i}" for i in range(len(paras))]


def normalize_file(path: Path, profile: dict[str, Any]) -> FileProfile:
    raw, sha = _read_bytes(path)
    text = raw.decode("utf-8", errors="replace")
    warnings: list[str] = []
    ftype = _detect_type(path)
    parse_ok = True
    parse_errors: list[str] = []
    structured: list[dict[str, Any]] | None = None
    sections: list[str] = []
    entities: list[str] = []
    schema_hint = ""
    top_keys: list[str] = []

    excerpts_cfg = profile.get("excerpts") or {}
    try:
        max_plain_chunks = int(excerpts_cfg.get("max_plaintext_chunks", 0))
    except (TypeError, ValueError):
        max_plain_chunks = 0

    norm_cfg = profile.get("normalization") or {}
    wrappers = norm_cfg.get("wrapper_flatten") or []
    aliases = norm_cfg.get("key_aliases") or {}
    if isinstance(aliases, dict):
        alias_map = {str(k): str(v) for k, v in aliases.items()}
    else:
        alias_map = {}

    data: Any = None

    if ftype == "json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            parse_ok = False
            parse_errors.append(str(e))
            data = None
    elif ftype == "yaml":
        if yaml is None:
            parse_ok = False
            parse_errors.append("PyYAML not installed")
        else:
            try:
                data = yaml.safe_load(text)
            except Exception as e:  # noqa: BLE001
                parse_ok = False
                parse_errors.append(str(e))
                data = None
    elif ftype in ("markdown", "plaintext", "unknown"):
        data = None
        sections = _markdown_sections(text) if ftype == "markdown" else _plaintext_chunks(text, max_plain_chunks)
        entities = list(sections)
    elif ftype == "code":
        data = None
        sections = [f"line:{i+1}" for i in range(len(text.splitlines()))]
        entities = []

    if isinstance(data, dict):
        top_keys = sorted(str(k) for k in data.keys())
        data = deepcopy(data)
        data = _flatten_wrappers(data, wrappers if isinstance(wrappers, list) else [], warnings)
        schema_hint = _schema_hint(data)
        raw_records = _extract_records(data, warnings)
        if raw_records:
            structured = []
            for rec in raw_records:
                if isinstance(rec, dict):
                    structured.append(_apply_key_aliases(dict(rec), alias_map, warnings))
        evidence_cfg = profile.get("evidence") or {}
        id_fields = evidence_cfg.get("entity_id_fields") or ["taxonomy_id", "id"]
        if structured:
            entities = _entity_ids_from_records(structured, list(id_fields))
        # sections from json: use taxonomy_id or id list
        sections = list(entities)

    req = _required_fields_for(profile, schema_hint, path.name)
    if structured and req:
        for i, rec in enumerate(structured):
            for f in req:
                if f not in rec or rec[f] in (None, "", []):
                    warnings.append(f"Record index {i} missing required field {f!r}.")

    if ftype == "unknown" and data is None and not sections:
        warnings.append("Unknown file type; using plain text fallback.")
        sections = _plaintext_chunks(text, max_plain_chunks)

    return FileProfile(
        path=str(path.resolve()),
        file_type=ftype if ftype != "unknown" or data is not None else "plaintext",
        raw_text=text,
        byte_size=len(raw),
        sha256_hex=sha,
        parse_ok=parse_ok,
        parse_errors=parse_errors,
        structured_records=structured,
        section_candidates=sections,
        entity_candidates=entities,
        normalization_warnings=warnings,
        schema_hint=schema_hint,
        top_level_keys=top_keys,
    )
