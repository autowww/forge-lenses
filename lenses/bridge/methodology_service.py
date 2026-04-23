"""Sprint B2: OGS-backed methodology artifacts, decisions, packs, ingest, readiness."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lenses.bridge.methodology_b2_registry import load_methodology_b2_registry
from lenses.orchestration_graph.constants import EDGE_KINDS, ENTITY_KINDS
from lenses.orchestration_graph.query import _row_edge, fetch_entity
from lenses.bridge.trace_service import insert_bridge_link


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _simple_yamlish(block: str) -> dict[str, Any]:
    """Parse minimal ``key: value`` / list lines without PyYAML dependency."""
    out: dict[str, Any] = {}
    cur_list_key: str | None = None
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- "):
            if cur_list_key:
                lst = out.get(cur_list_key)
                if not isinstance(lst, list):
                    lst = []
                    out[cur_list_key] = lst
                lst.append(stripped[2:].strip().strip("'\""))
            continue
        if ":" in stripped:
            k, v = stripped.split(":", 1)
            key = k.strip()
            val = v.strip().strip("'\"")
            cur_list_key = None
            if not val:
                out[key] = []
                cur_list_key = key
            else:
                low = val.lower()
                if low in ("true", "false"):
                    out[key] = low == "true"
                else:
                    try:
                        out[key] = int(val)
                    except ValueError:
                        out[key] = val
    return out


def _parse_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    """Return (frontmatter dict, body after frontmatter)."""
    if not raw.startswith("---"):
        return {}, raw
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?", raw, re.DOTALL)
    if not m:
        return {}, raw
    block = m.group(1)
    body = raw[m.end() :]
    return _simple_yamlish(block), body


def _entity_id_for_path(rel_posix: str) -> str:
    h = _sha256_text(rel_posix)[:16]
    return f"ogs:b2:md:{h}"


def upsert_ogs_entity(
    conn: sqlite3.Connection,
    *,
    entity_id: str,
    kind: str,
    display_name: str,
    summary: str,
    payload: dict[str, Any],
    external_ref: str = "",
    source_system: str = "methodology_b2",
    source_record_id: str = "",
) -> None:
    if kind not in ENTITY_KINDS:
        raise ValueError(f"invalid entity kind: {kind}")
    now = _now_iso()
    payload_s = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    conn.execute(
        """
        INSERT INTO ogs_entity (
          id, kind, display_name, summary, payload_json, external_ref,
          source_system, source_record_id, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
          kind = excluded.kind,
          display_name = excluded.display_name,
          summary = excluded.summary,
          payload_json = excluded.payload_json,
          external_ref = excluded.external_ref,
          source_system = excluded.source_system,
          source_record_id = excluded.source_record_id,
          updated_at = excluded.updated_at
        """,
        (
            entity_id,
            kind,
            display_name,
            summary[:2000],
            payload_s,
            external_ref,
            source_system,
            source_record_id,
            now,
            now,
        ),
    )


def _index_doc(conn: sqlite3.Connection, rel_path: str, entity_id: str, checksum: str) -> None:
    conn.execute(
        """
        INSERT INTO bridge_evidence_doc_index (rel_path, entity_id, checksum, ingested_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(rel_path) DO UPDATE SET
          entity_id = excluded.entity_id,
          checksum = excluded.checksum,
          ingested_at = excluded.ingested_at
        """,
        (rel_path, entity_id, checksum, _now_iso()),
    )


def list_artifacts(conn: sqlite3.Connection, *, limit: int = 100, offset: int = 0) -> dict[str, Any]:
    lim = max(1, min(limit, 500))
    off = max(0, offset)
    rows = conn.execute(
        """
        SELECT id, kind, display_name, summary, payload_json, external_ref, updated_at
        FROM ogs_entity
        WHERE kind = 'methodology_artifact'
        ORDER BY updated_at DESC
        LIMIT ? OFFSET ?
        """,
        (lim, off),
    ).fetchall()
    items = []
    for r in rows:
        try:
            p = json.loads(r["payload_json"] or "{}")
        except json.JSONDecodeError:
            p = {}
        items.append(
            {
                "id": r["id"],
                "display_name": r["display_name"],
                "summary": r["summary"] or "",
                "updated_at": r["updated_at"],
                "payload": p if isinstance(p, dict) else {},
            }
        )
    total = int(conn.execute("SELECT COUNT(*) AS c FROM ogs_entity WHERE kind='methodology_artifact'").fetchone()["c"])
    return {"ok": True, "artifacts": items, "total": total, "limit": lim, "offset": off}


def list_decisions(conn: sqlite3.Connection, *, limit: int = 100, offset: int = 0) -> dict[str, Any]:
    lim = max(1, min(limit, 500))
    off = max(0, offset)
    rows = conn.execute(
        """
        SELECT id, kind, display_name, summary, payload_json, updated_at
        FROM ogs_entity
        WHERE kind = 'decision_record'
        ORDER BY updated_at DESC
        LIMIT ? OFFSET ?
        """,
        (lim, off),
    ).fetchall()
    items = []
    for r in rows:
        try:
            p = json.loads(r["payload_json"] or "{}")
        except json.JSONDecodeError:
            p = {}
        items.append(
            {
                "id": r["id"],
                "display_name": r["display_name"],
                "summary": r["summary"] or "",
                "updated_at": r["updated_at"],
                "payload": p if isinstance(p, dict) else {},
            }
        )
    total = int(conn.execute("SELECT COUNT(*) AS c FROM ogs_entity WHERE kind='decision_record'").fetchone()["c"])
    return {"ok": True, "decisions": items, "total": total, "limit": lim, "offset": off}


def get_entity_bundle(conn: sqlite3.Connection, entity_id: str) -> dict[str, Any]:
    ent = fetch_entity(conn, entity_id)
    if ent is None:
        return {"ok": False, "error": "entity_not_found"}
    out_e = [_row_edge(r) for r in conn.execute("SELECT * FROM ogs_edge WHERE from_id = ?", (entity_id,))]
    in_e = [_row_edge(r) for r in conn.execute("SELECT * FROM ogs_edge WHERE to_id = ?", (entity_id,))]
    doc = conn.execute(
        "SELECT rel_path, checksum, ingested_at FROM bridge_evidence_doc_index WHERE entity_id = ?",
        (entity_id,),
    ).fetchone()
    doc_row = None
    if doc:
        doc_row = {
            "rel_path": doc["rel_path"],
            "checksum": doc["checksum"] or "",
            "ingested_at": doc["ingested_at"] or "",
        }
    return {
        "ok": True,
        "entity": ent,
        "outgoing_edges": out_e,
        "incoming_edges": in_e,
        "source_document": doc_row,
    }


def create_decision(conn: sqlite3.Connection, body: dict[str, Any]) -> dict[str, Any]:
    reg = load_methodology_b2_registry()
    profiles = reg.get("decision_type_profiles") or {}
    dtype = str(body.get("decision_type") or "").strip().lower()
    if dtype not in profiles:
        return {"ok": False, "error": "invalid_decision_type", "allowed": list(profiles.keys())}
    title = str(body.get("title") or "Untitled decision").strip()
    eid = str(body.get("id") or "").strip() or f"ogs:b2:dec:{_sha256_text(title + dtype)[:12]}"
    prof = profiles.get(dtype) or {}
    binding = bool(body.get("binding", prof.get("binding_default", False)))
    payload: dict[str, Any] = {
        "decision_type": dtype,
        "problem_statement": str(body.get("problem_statement") or ""),
        "decision_summary": str(body.get("decision_summary") or body.get("summary") or ""),
        "alternatives_considered": body.get("alternatives_considered") or [],
        "rationale": str(body.get("rationale") or ""),
        "impact": str(body.get("impact") or ""),
        "owner": str(body.get("owner") or ""),
        "binding": binding,
        "signoff_state": "draft",
        "gates_allowed": list(prof.get("gates") or []),
    }
    summary = payload["decision_summary"][:500] or title
    upsert_ogs_entity(
        conn,
        entity_id=eid,
        kind="decision_record",
        display_name=title,
        summary=summary,
        payload=payload,
        source_record_id=dtype,
    )
    conn.commit()
    return {"ok": True, "id": eid}


def signoff_decision(
    conn: sqlite3.Connection,
    entity_id: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    reg = load_methodology_b2_registry()
    profiles = reg.get("decision_type_profiles") or {}
    ent = fetch_entity(conn, entity_id)
    if ent is None or str(ent.get("kind")) != "decision_record":
        return {"ok": False, "error": "decision_not_found"}
    payload = ent.get("payload") if isinstance(ent.get("payload"), dict) else {}
    dtype = str(payload.get("decision_type") or "")
    prof = profiles.get(dtype) or {}
    binding = bool(payload.get("binding"))
    if binding and prof.get("human_signoff_required_for_binding"):
        if not bool(body.get("confirm_human_signoff")):
            return {
                "ok": False,
                "error": "human_signoff_required",
                "detail": "Set confirm_human_signoff:true for binding ADR/Directive.",
            }
    signed_by = str(body.get("signed_by") or body.get("login") or "unknown").strip() or "unknown"
    payload = dict(payload)
    payload["signoff_state"] = "signed"
    payload["signed_at"] = _now_iso()
    payload["signed_by"] = signed_by
    now = _now_iso()
    conn.execute(
        """
        UPDATE ogs_entity SET payload_json = ?, summary = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            json.dumps(payload, separators=(",", ":"), sort_keys=True),
            str(payload.get("decision_summary") or ent.get("summary") or "")[:500],
            now,
            entity_id,
        ),
    )
    conn.commit()
    return {"ok": True, "id": entity_id, "payload": payload}


def _heuristic_kind(rel_posix: str) -> dict[str, Any] | None:
    low = rel_posix.lower()
    if "adr" in low and low.endswith(".md"):
        return {"kind": "decision", "decision_type": "adr", "title_hint": "ADR"}
    if "directive" in low and low.endswith(".md"):
        return {"kind": "decision", "decision_type": "directive", "title_hint": "Directive"}
    if "ember" in low and "log" in low and low.endswith(".md"):
        return {"kind": "decision", "decision_type": "ember_log", "title_hint": "Ember Log"}
    if "assay" in low and low.endswith(".md"):
        return {"kind": "artifact", "forge_profile": "assay_packet"}
    if "review-pack" in low or "review_pack" in low:
        return {"kind": "artifact", "forge_profile": "review_pack"}
    return None


def import_markdown_paths(
    workspace_root: Path,
    conn: sqlite3.Connection,
    *,
    rel_paths: list[str] | None = None,
    scan_roots: list[str] | None = None,
) -> dict[str, Any]:
    reg = load_methodology_b2_registry()
    defaults = reg.get("ingest_defaults") or {}
    max_bytes = int(defaults.get("max_file_bytes") or 524288)
    root = workspace_root.resolve()
    files: list[Path] = []
    if rel_paths:
        for rp in rel_paths:
            p = (root / rp).resolve()
            if not str(p).startswith(str(root)) or not p.is_file():
                continue
            if p.suffix.lower() == ".md":
                files.append(p)
    else:
        roots = scan_roots or list(defaults.get("scan_roots") or ["forge", "docs"])
        for sr in roots:
            base = root / sr
            if base.is_dir():
                for p in base.rglob("*.md"):
                    if p.is_file():
                        files.append(p)
    imported: list[dict[str, Any]] = []
    errors: list[str] = []
    for p in files:
        rel = str(p.relative_to(root)).replace("\\", "/")
        try:
            raw_bytes = p.read_bytes()
            if len(raw_bytes) > max_bytes:
                errors.append(f"skip_too_large:{rel}")
                continue
            raw = raw_bytes.decode("utf-8", errors="replace")
            fm, _body = _parse_frontmatter(raw)
            lm: dict[str, Any] = {}
            if isinstance(fm.get("lenses_methodology"), dict):
                lm.update(fm["lenses_methodology"])  # type: ignore[index]
            for flat_k, lm_k in (
                ("lenses_methodology_kind", "kind"),
                ("lenses_decision_type", "decision_type"),
                ("lenses_forge_profile", "forge_profile"),
                ("lenses_skip_index", "lenses_skip_index"),
            ):
                if flat_k in fm and fm[flat_k] is not None:
                    lm[lm_k] = fm[flat_k]
            lat = str(fm.get("lenses_artifact_type") or lm.get("artifact_type") or "").strip().lower()
            hint = _heuristic_kind(rel)
            checksum = _sha256_bytes(raw_bytes)
            eid = _entity_id_for_path(rel)

            kind = str(lm.get("kind") or fm.get("lenses_ingest_kind") or "").strip().lower()
            prof_keys = reg.get("forge_artifact_profiles") or {}
            if not kind and lat:
                kind = "artifact" if lat in prof_keys else ""
            if not kind and hint:
                kind = str(hint.get("kind") or "")
            if not kind:
                fp = str(lm.get("forge_profile") or fm.get("lenses_forge_profile") or "").strip()
                if fp and fp in prof_keys:
                    kind = "artifact"

            if lm.get("lenses_skip_index") or fm.get("lenses_skip_index"):
                continue

            if kind == "decision" or (hint and hint.get("kind") == "decision" and not lat):
                dtype = str(
                    lm.get("decision_type") or fm.get("lenses_decision_type") or hint.get("decision_type") or "adr"
                ).strip().lower()
                title = str(fm.get("title") or lm.get("title") or hint.get("title_hint") or p.stem)
                profiles = reg.get("decision_type_profiles") or {}
                prof = profiles.get(dtype, {})
                payload = {
                    "decision_type": dtype,
                    "problem_statement": str(lm.get("problem_statement") or ""),
                    "decision_summary": str(lm.get("summary") or fm.get("description") or "")[:2000],
                    "alternatives_considered": lm.get("alternatives_considered") or [],
                    "rationale": str(lm.get("rationale") or ""),
                    "impact": str(lm.get("impact") or ""),
                    "owner": str(lm.get("owner") or ""),
                    "binding": bool(lm.get("binding", prof.get("binding_default", False))),
                    "signoff_state": str(lm.get("signoff_state") or "imported"),
                    "gates_allowed": list(prof.get("gates") or []),
                    "source_path": rel,
                    "content_fingerprint": checksum,
                }
                upsert_ogs_entity(
                    conn,
                    entity_id=eid,
                    kind="decision_record",
                    display_name=title,
                    summary=payload["decision_summary"][:500],
                    payload=payload,
                    external_ref=f"file:{rel}",
                    source_record_id=checksum[:16],
                )
                _index_doc(conn, rel, eid, checksum)
                imported.append({"rel_path": rel, "entity_id": eid, "kind": "decision_record"})
            elif kind == "artifact" or lat or (hint and hint.get("kind") == "artifact"):
                forge_profile = str(
                    lm.get("forge_profile") or fm.get("lenses_forge_profile") or lat or hint.get("forge_profile") or "implementation_evidence"
                )
                profiles_map = reg.get("forge_artifact_profiles") or {}
                prof = profiles_map.get(forge_profile, {})
                title = str(fm.get("title") or lm.get("title") or p.stem)
                payload = {
                    "artifact_type": str(lm.get("artifact_type") or "markdown"),
                    "bridge_type": str(lm.get("bridge_type") or forge_profile),
                    "forge_profile": forge_profile,
                    "neutral_category": str(prof.get("neutral_category") or "evidence"),
                    "evidence_phase": str(prof.get("evidence_phase") or "implementation"),
                    "status": str(lm.get("status") or "imported"),
                    "source_path": rel,
                    "source_url": str(lm.get("source_url") or ""),
                    "version": str(lm.get("version") or "1"),
                    "content_fingerprint": checksum,
                    "owner": str(lm.get("owner") or ""),
                    "approved_by": str(lm.get("approved_by") or ""),
                    "validity_date": str(lm.get("validity_date") or ""),
                    "lineage_note": "Imported from workspace markdown; graph edges define methodology links.",
                }
                if forge_profile == "review_pack":
                    ent_kind = "review_pack"
                    payload.setdefault("template_id", "imported")
                elif forge_profile == "assay_packet":
                    ent_kind = "assay_packet"
                    payload.setdefault("primary_release_id", "")
                else:
                    ent_kind = "methodology_artifact"
                upsert_ogs_entity(
                    conn,
                    entity_id=eid,
                    kind=ent_kind,
                    display_name=title,
                    summary=str(fm.get("description") or lm.get("summary") or "")[:500],
                    payload=payload,
                    external_ref=f"file:{rel}",
                    source_record_id=checksum[:16],
                )
                _index_doc(conn, rel, eid, checksum)
                imported.append({"rel_path": rel, "entity_id": eid, "kind": ent_kind})
        except OSError as ex:
            errors.append(f"{rel}:{ex}")
    conn.commit()
    return {"ok": True, "imported": imported, "errors": errors, "count": len(imported)}


def evidence_search(conn: sqlite3.Connection, q: str, *, limit: int = 50) -> dict[str, Any]:
    lim = max(1, min(limit, 200))
    qt = q.strip()
    if qt:
        term = f"%{qt}%"
        rows = conn.execute(
            """
            SELECT e.id, e.kind, e.display_name, e.summary, i.rel_path
            FROM ogs_entity e
            LEFT JOIN bridge_evidence_doc_index i ON i.entity_id = e.id
            WHERE e.kind IN ('methodology_artifact', 'decision_record', 'review_pack', 'assay_packet')
              AND (
                e.display_name LIKE ? OR e.summary LIKE ? OR i.rel_path LIKE ? OR e.payload_json LIKE ?
              )
            ORDER BY e.updated_at DESC
            LIMIT ?
            """,
            (term, term, term, term, lim),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT e.id, e.kind, e.display_name, e.summary, i.rel_path
            FROM ogs_entity e
            LEFT JOIN bridge_evidence_doc_index i ON i.entity_id = e.id
            WHERE e.kind IN ('methodology_artifact', 'decision_record', 'review_pack', 'assay_packet')
            ORDER BY e.updated_at DESC
            LIMIT ?
            """,
            (lim,),
        ).fetchall()
    hits = [
        {
            "id": r["id"],
            "kind": r["kind"],
            "display_name": r["display_name"],
            "summary": r["summary"] or "",
            "rel_path": r["rel_path"] or "",
        }
        for r in rows
    ]
    return {"ok": True, "query": qt, "hits": hits}


def build_review_pack_view(conn: sqlite3.Connection, pack_id: str) -> dict[str, Any]:
    ent = fetch_entity(conn, pack_id)
    if ent is None or str(ent.get("kind")) != "review_pack":
        return {"ok": False, "error": "review_pack_not_found"}
    payload = ent.get("payload") if isinstance(ent.get("payload"), dict) else {}
    work_units: list[str] = []
    code_links: list[str] = []
    evidence: list[str] = []
    decisions: list[str] = []
    for row in conn.execute("SELECT * FROM ogs_edge WHERE from_id = ?", (pack_id,)):
        e = _row_edge(row)
        tid = str(e["to_id"])
        other = fetch_entity(conn, tid)
        if not other:
            continue
        k = str(other.get("kind"))
        if k in ("story", "task", "epic"):
            work_units.append(tid)
        elif k in ("change_request", "commit", "build"):
            code_links.append(tid)
        elif k in ("evidence", "methodology_artifact"):
            evidence.append(tid)
        elif k == "decision_record":
            decisions.append(tid)
    source_inputs = [
        str(x[0])
        for x in conn.execute(
            "SELECT rel_path FROM bridge_evidence_doc_index WHERE entity_id = ?",
            (pack_id,),
        ).fetchall()
    ]
    return {
        "ok": True,
        "pack": ent,
        "sections": {
            "work_units": work_units,
            "linked_code": code_links,
            "evidence_attachments": evidence,
            "outstanding_decisions": decisions,
            "known_risks": list(payload.get("known_risks") or []),
            "test_results_summary": payload.get("test_results_summary") or "",
        },
        "source_inputs": source_inputs,
        "generated_sections": list(payload.get("generated_sections") or []),
    }


def build_assay_packet_view(conn: sqlite3.Connection, packet_id: str) -> dict[str, Any]:
    ent = fetch_entity(conn, packet_id)
    if ent is None or str(ent.get("kind")) != "assay_packet":
        return {"ok": False, "error": "assay_packet_not_found"}
    payload = ent.get("payload") if isinstance(ent.get("payload"), dict) else {}
    release_candidates: list[str] = []
    evidence_links: list[str] = []
    exceptions: list[str] = []
    for row in conn.execute("SELECT * FROM ogs_edge WHERE from_id = ?", (packet_id,)):
        e = _row_edge(row)
        tid = str(e["to_id"])
        other = fetch_entity(conn, tid)
        if not other:
            continue
        k = str(other.get("kind"))
        if k == "release":
            release_candidates.append(tid)
        elif k in ("build", "artifact", "evidence", "methodology_artifact"):
            evidence_links.append(tid)
        elif k == "compliance_exception":
            exceptions.append(tid)
    source_inputs = [
        str(x[0])
        for x in conn.execute(
            "SELECT rel_path FROM bridge_evidence_doc_index WHERE entity_id = ?",
            (packet_id,),
        ).fetchall()
    ]
    readiness = readiness_gaps_for_release(conn, str(payload.get("primary_release_id") or ""))
    return {
        "ok": True,
        "packet": ent,
        "sections": {
            "release_candidates": release_candidates,
            "quality_security_compliance": payload.get("quality_security_compliance") or {},
            "evidence_links": evidence_links,
            "approvals": list(payload.get("approvals") or []),
            "exception_records": exceptions,
            "recommended_outcome": payload.get("recommended_decision_outcome") or "",
        },
        "source_inputs": source_inputs,
        "readiness_gaps": readiness.get("gaps", []) if readiness.get("ok") else [],
    }


def readiness_gaps_for_release(conn: sqlite3.Connection, release_id: str) -> dict[str, Any]:
    if not release_id.strip():
        return {"ok": False, "error": "missing_release_id", "gaps": []}
    rel = fetch_entity(conn, release_id)
    if rel is None or str(rel.get("kind")) != "release":
        return {"ok": False, "error": "release_not_found", "gaps": []}
    gaps: list[dict[str, Any]] = []
    # Linked assay_packet via references -> release
    ap = conn.execute(
        """
        SELECT e.id FROM ogs_entity e
        JOIN ogs_edge ed ON ed.from_id = e.id AND ed.to_id = ? AND ed.kind IN ('references','approves','aggregates')
        WHERE e.kind = 'assay_packet'
        LIMIT 5
        """,
        (release_id,),
    ).fetchone()
    if not ap:
        gaps.append(
            {
                "kind": "missing_required_artifact",
                "artifact": "assay_packet",
                "detail": "No assay_packet entity references this release — add one for gate readiness.",
            }
        )
    signed_dir = False
    for r in conn.execute("SELECT payload_json FROM ogs_entity WHERE kind = 'decision_record'"):
        try:
            p = json.loads(r["payload_json"] or "{}")
        except json.JSONDecodeError:
            continue
        if (
            p.get("decision_type") == "directive"
            and p.get("signoff_state") == "signed"
            and p.get("binding")
        ):
            signed_dir = True
            break
    if not signed_dir:
        gaps.append(
            {
                "kind": "missing_governance_decision",
                "artifact": "directive",
                "detail": "No signed binding Directive found in graph (demo heuristic).",
            }
        )
    return {"ok": True, "release_id": release_id, "gaps": gaps}


def create_review_pack(conn: sqlite3.Connection, body: dict[str, Any]) -> dict[str, Any]:
    title = str(body.get("title") or "Review Pack").strip()
    eid = str(body.get("id") or "").strip() or f"ogs:b2:rp:{_sha256_text(title)[:12]}"
    payload = {
        "template_id": str(body.get("template_id") or "default"),
        "known_risks": body.get("known_risks") or [],
        "test_results_summary": str(body.get("test_results_summary") or ""),
        "generated_sections": body.get("generated_sections") or [],
    }
    upsert_ogs_entity(
        conn,
        entity_id=eid,
        kind="review_pack",
        display_name=title,
        summary=str(body.get("summary") or "")[:500],
        payload=payload,
    )
    conn.commit()
    return {"ok": True, "id": eid}


def create_assay_packet(conn: sqlite3.Connection, body: dict[str, Any]) -> dict[str, Any]:
    title = str(body.get("title") or "Assay Packet").strip()
    eid = str(body.get("id") or "").strip() or f"ogs:b2:ap:{_sha256_text(title)[:12]}"
    payload = {
        "primary_release_id": str(body.get("primary_release_id") or ""),
        "quality_security_compliance": body.get("quality_security_compliance") or {},
        "approvals": body.get("approvals") or [],
        "recommended_decision_outcome": str(body.get("recommended_decision_outcome") or ""),
        "generated_sections": body.get("generated_sections") or [],
    }
    upsert_ogs_entity(
        conn,
        entity_id=eid,
        kind="assay_packet",
        display_name=title,
        summary=str(body.get("summary") or "")[:500],
        payload=payload,
    )
    conn.commit()
    return {"ok": True, "id": eid}


def link_entities(
    conn: sqlite3.Connection,
    from_id: str,
    to_id: str,
    edge_kind: str,
) -> dict[str, Any]:
    if edge_kind not in EDGE_KINDS:
        return {"ok": False, "error": "invalid_edge_kind"}
    return insert_bridge_link(conn, from_id=from_id, to_id=to_id, kind=edge_kind, source_system="methodology_b2")
