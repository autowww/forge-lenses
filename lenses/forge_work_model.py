"""Normalized Forge work graph: milestones, epics, stories, sparks, docs, decisions, sessions."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlencode

from lenses.forge_spine import (
    index_versona_sessions,
    parse_charge_sparks,
)
from lenses.roadmap_outline import extract_gantt_model
from lenses.safe_forge_paths import roadmap_timeline_view_link, workspace_md_view_link
from lenses.wbs_model import WBS_ID_RE, WbsModel, parse_wbs_markdown

NodeKind = Literal[
    "milestone",
    "epic",
    "story",
    "spark",
    "documentRef",
    "decisionRef",
    "sessionRef",
]

_EPIC_ID_RE = re.compile(r"^(M\d+E\d+)$")
_MILESTONE_SCHEDULE_RE = re.compile(r"^M\d+\.\d+$")


def _epic_key_from_story_id(sid: str) -> str:
    m = re.match(r"^(M\d+E\d+)S\d+", sid)
    return m.group(1) if m else ""


def _milestone_key_from_epic(eid: str) -> str:
    m = re.match(r"^(M\d+)", eid)
    return m.group(1) if m else ""


def _doc_node_id(rel_path: str) -> str:
    return f"doc:{rel_path.replace(chr(92), '/')}"


@dataclass
class WorkNode:
    id: str
    kind: str
    title: str
    parent_id: str | None = None
    status: str | None = None
    horizon: str | None = None
    blockers: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    provenance: list[dict[str, str]] = field(default_factory=list)
    synthesized: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ForgeWorkModel:
    """In-memory work graph with selector helpers."""

    repo_hint: str
    nodes: dict[str, WorkNode] = field(default_factory=dict)
    root_ids: list[str] = field(default_factory=list)
    sources_present: dict[str, bool] = field(default_factory=dict)

    def get_node(self, node_id: str) -> WorkNode | None:
        return self.nodes.get(node_id)

    def children(self, node_id: str) -> list[WorkNode]:
        return [self.nodes[c] for c in self._child_ids(node_id) if c in self.nodes]

    def _child_ids(self, node_id: str) -> list[str]:
        return sorted(nid for nid, n in self.nodes.items() if n.parent_id == node_id)

    def ancestors(self, node_id: str) -> list[WorkNode]:
        out: list[WorkNode] = []
        cur = self.nodes.get(node_id)
        seen: set[str] = set()
        while cur and cur.parent_id and cur.parent_id not in seen:
            seen.add(cur.id)
            p = self.nodes.get(cur.parent_id)
            if p:
                out.append(p)
                cur = p
            else:
                break
        return list(reversed(out))

    def summary(self, node_id: str) -> dict[str, Any]:
        n = self.nodes.get(node_id)
        if not n:
            return {"id": node_id, "missing": True}
        return {
            "id": n.id,
            "kind": n.kind,
            "title": n.title,
            "status": n.status,
            "horizon": n.horizon,
            "synthesized": n.synthesized,
            "provenance": n.provenance,
        }

    def related_execution(self, node_id: str) -> dict[str, Any]:
        n = self.nodes.get(node_id)
        if not n:
            return {"charge": [], "notes": []}
        return {
            "charge": n.extra.get("charge_rows", []),
            "notes": n.extra.get("execution_notes", []),
        }

    def related_evidence_nodes(self, node_id: str) -> tuple[list[WorkNode], list[WorkNode]]:
        n = self.nodes.get(node_id)
        if not n:
            return [], []
        dec = [
            self.nodes[did]
            for did in n.extra.get("decision_ref_ids", [])
            if did in self.nodes
        ]
        sess = [
            self.nodes[sid]
            for sid in n.extra.get("session_ref_ids", [])
            if sid in self.nodes
        ]
        return dec, sess

    def related_product_docs(self, node_id: str) -> list[WorkNode]:
        n = self.nodes.get(node_id)
        if not n:
            return []
        return [
            self.nodes[did]
            for did in n.extra.get("document_ref_ids", [])
            if did in self.nodes
        ]

    def to_json_blob(self) -> dict[str, Any]:
        return {
            "repo_hint": self.repo_hint,
            "root_ids": self.root_ids,
            "sources_present": self.sources_present,
            "nodes": {k: asdict(v) for k, v in sorted(self.nodes.items())},
        }


def _prov(path: str, role: str) -> dict[str, str]:
    p = path.replace("\\", "/")
    if role == "roadmap":
        vh = roadmap_timeline_view_link(p)
    elif role == "wbs":
        vh = f"/wbs/view?{urlencode({'p': p})}"
    else:
        vh = workspace_md_view_link(p)
    return {
        "path": p,
        "role": role,
        "view_href": vh,
    }


def _walk_product_docs(
    base: Path, workspace_root: Path, *, max_files: int = 120
) -> list[str]:
    prod = base / "docs" / "product"
    if not prod.is_dir():
        return []
    out: list[str] = []
    for fp in sorted(prod.rglob("*.md")):
        if fp.is_file():
            try:
                rel = str(fp.resolve().relative_to(workspace_root.resolve()))
            except ValueError:
                continue
            out.append(rel.replace("\\", "/"))
            if len(out) >= max_files:
                break
    return out


def _index_ember_decisions(
    workspace_root: Path,
    base: Path,
    *,
    limit_files: int = 25,
) -> tuple[list[dict[str, Any]], list[WorkNode]]:
    ember = base / "ember-logs"
    node_list: list[WorkNode] = []
    if not ember.is_dir():
        return [], []
    files = sorted(
        [x for x in ember.glob("*.md") if x.is_file()],
        key=lambda x: x.name,
        reverse=True,
    )[:limit_files]
    raw_index: list[dict[str, Any]] = []
    for fp in files:
        try:
            rel = str(fp.resolve().relative_to(workspace_root.resolve())).replace(
                "\\", "/"
            )
        except ValueError:
            continue
        text = fp.read_text(encoding="utf-8", errors="replace")
        parts = re.split(r"(?m)^##\s+Decision:", text)
        for i, chunk in enumerate(parts[1:], start=1):
            did = f"ember:{rel}#{i}"
            title = (chunk.split("\n", 1)[0]).strip()[:120] or f"Decision {i}"
            node_list.append(
                WorkNode(
                    id=did,
                    kind="decisionRef",
                    title=title,
                    provenance=[_prov(rel, "ember")],
                    extra={"snippet": ("## Decision:" + chunk).strip()[:900]},
                )
            )
            raw_index.append(
                {
                    "id": did,
                    "file_rel": rel,
                    "ids_in_text": list({m.group(1) for m in WBS_ID_RE.finditer(chunk)}),
                }
            )
    return raw_index, node_list



def build_forge_work_model(
    workspace_root: Path,
    *,
    repo_hint: str,
    wbs_rel: str,
    roadmap_rel: str | None = None,
) -> ForgeWorkModel:
    wr = workspace_root.resolve()
    base = wr / repo_hint if repo_hint else wr
    sources: dict[str, bool] = {
        "wbs": False,
        "roadmap": False,
        "charge": False,
        "ember_logs": False,
        "versona": False,
        "product_docs": False,
    }

    wbs_path = wr / wbs_rel.replace("\\", "/").strip("/")
    if not wbs_path.is_file():
        return ForgeWorkModel(repo_hint=repo_hint, sources_present=sources)

    sources["wbs"] = True
    wbs_text = wbs_path.read_text(encoding="utf-8", errors="replace")
    wbs: WbsModel = parse_wbs_markdown(wbs_rel, wbs_text)

    nodes: dict[str, WorkNode] = {}

    def add_node(n: WorkNode) -> None:
        nodes[n.id] = n

    wbs_prov = _prov(wbs_rel, "wbs")

    if roadmap_rel:
        rp = wr / roadmap_rel.replace("\\", "/").strip("/")
        if rp.is_file():
            sources["roadmap"] = True
            roadmap_md = rp.read_text(encoding="utf-8", errors="replace")
            gantt = extract_gantt_model(roadmap_md)
            for mid in gantt.get("milestones") or []:
                if isinstance(mid, str) and _MILESTONE_SCHEDULE_RE.match(mid.strip()):
                    smid = mid.strip()
                    if smid not in nodes:
                        add_node(
                            WorkNode(
                                id=smid,
                                kind="milestone",
                                title=f"Roadmap window {smid}",
                                provenance=[_prov(roadmap_rel, "roadmap")],
                                extra={"schedule": True},
                            )
                        )

    milestone_keys: set[str] = set()
    for ek, _title, _th in wbs.epics:
        if _EPIC_ID_RE.match(ek):
            mk = _milestone_key_from_epic(ek)
            if mk:
                milestone_keys.add(mk)

    for mk in sorted(milestone_keys):
        m_ex: dict[str, Any] = {"layer": "product_spark"}
        bo = (wbs.milestone_outcomes or {}).get(mk, "").strip()
        if bo:
            m_ex["business_outcome"] = bo
        add_node(
            WorkNode(
                id=mk,
                kind="milestone",
                title=f"Milestone {mk}",
                parent_id=None,
                provenance=[wbs_prov],
                synthesized=False,
                extra=m_ex,
            )
        )

    epic_keys_seen: set[str] = set()
    for ek, epic_heading, _th in wbs.epics:
        if not _EPIC_ID_RE.match(ek):
            continue
        epic_keys_seen.add(ek)
        mk = _milestone_key_from_epic(ek)
        add_node(
            WorkNode(
                id=ek,
                kind="epic",
                title=epic_heading,
                parent_id=mk if mk in nodes else None,
                provenance=[wbs_prov],
            )
        )

    for sid, st in wbs.stories.items():
        ek = _epic_key_from_story_id(sid)
        if ek and ek not in epic_keys_seen:
            add_node(
                WorkNode(
                    id=ek,
                    kind="epic",
                    title=f"Epic {ek}",
                    parent_id=_milestone_key_from_epic(ek) or None,
                    provenance=[wbs_prov],
                    synthesized=True,
                )
            )
            epic_keys_seen.add(ek)
        doc_ids: list[str] = []
        for pth in st.product_paths:
            did = _doc_node_id(pth)
            if did not in nodes:
                add_node(
                    WorkNode(
                        id=did,
                        kind="documentRef",
                        title=pth,
                        provenance=[_prov(pth, "product_doc")],
                        extra={"path": pth},
                    )
                )
            doc_ids.append(did)

        deps = list(st.dependencies)
        pri = (st.priority or "").strip()
        add_node(
            WorkNode(
                id=sid,
                kind="story",
                title=st.title,
                parent_id=ek if ek in nodes else None,
                dependencies=deps,
                provenance=[wbs_prov],
                extra={
                    "document_ref_ids": doc_ids,
                    "acceptance_summary": st.acceptance_summary,
                    "priority": pri,
                },
            )
        )

    for tid, task in wbs.tasks.items():
        sid = task.story_id or re.sub(r"T\d+$", "", tid)
        blk = list(task.blockers)
        add_node(
            WorkNode(
                id=tid,
                kind="spark",
                title=task.title,
                parent_id=sid if sid in nodes else None,
                blockers=blk,
                provenance=[wbs_prov],
                extra={"phase": (task.row or {}).get("Phase", "")},
            )
        )

    charge_path = base / "forge" / "charge.md"
    if charge_path.is_file():
        sources["charge"] = True
        try:
            cr = str(charge_path.resolve().relative_to(wr)).replace("\\", "/")
        except ValueError:
            cr = "forge/charge.md"
        charge_rows = parse_charge_sparks(
            charge_path.read_text(encoding="utf-8", errors="replace")
        )
        for row in charge_rows:
            spid = row.get("spark_id", "")
            if spid in nodes and nodes[spid].kind == "spark":
                nodes[spid].status = str(row.get("status") or "")
                ch = nodes[spid].extra.setdefault("charge_rows", [])
                ch.append(row)
                nodes[spid].provenance = nodes[spid].provenance + [_prov(cr, "charge")]

    ember_ix, ember_nodes = _index_ember_decisions(wr, base)
    for en in ember_nodes:
        if en.id not in nodes:
            add_node(en)
    sources["ember_logs"] = bool(ember_ix)

    for entry in ember_ix:
        for wid in entry.get("ids_in_text") or []:
            if wid in nodes and nodes[wid].kind in ("story", "spark"):
                dids = nodes[wid].extra.setdefault("decision_ref_ids", [])
                if entry["id"] not in dids:
                    dids.append(entry["id"])

    versona_root = base / "forge-logs" / "versona"
    sessions = index_versona_sessions(wr, versona_root)
    if sessions:
        sources["versona"] = True
    for s in sessions:
        sid = f"session:{s.get('session_id', '')}"
        if sid in nodes:
            sid = f"session:{s.get('path', '')}"
        n = WorkNode(
            id=sid,
            kind="sessionRef",
            title=str(s.get("session_id", "session")),
            provenance=[_prov(str(s.get("path", "")), "versona")],
            extra=dict(s),
        )
        if sid not in nodes:
            add_node(n)
        for ref in s.get("work_item_refs") or []:
            r = str(ref).strip()
            if r in nodes and nodes[r].kind in ("story", "spark"):
                xs = nodes[r].extra.setdefault("session_ref_ids", [])
                if sid not in xs:
                    xs.append(sid)

    prod_rels = _walk_product_docs(base, wr)
    if prod_rels:
        sources["product_docs"] = True
    for prel in prod_rels:
        did = _doc_node_id(prel)
        if did not in nodes:
            add_node(
                WorkNode(
                    id=did,
                    kind="documentRef",
                    title=prel,
                    provenance=[_prov(prel, "product_doc")],
                    extra={"path": prel},
                )
            )

    roots = sorted(
        nid
        for nid, n in nodes.items()
        if n.kind == "milestone" and not n.parent_id
    )
    if not roots:
        roots = sorted(
            nid
            for nid, n in nodes.items()
            if n.parent_id is None and n.kind in ("epic", "milestone", "story")
        )

    return ForgeWorkModel(
        repo_hint=repo_hint,
        nodes=nodes,
        root_ids=roots,
        sources_present=sources,
    )


def work_model_selectors_payload(
    model: ForgeWorkModel, node_id: str
) -> dict[str, Any]:
    n = model.get_node(node_id)
    if not n:
        return {"ok": False, "error": "unknown_node", "node_id": node_id}
    dec, sess = model.related_evidence_nodes(node_id)
    return {
        "ok": True,
        "node_id": node_id,
        "summary": model.summary(node_id),
        "children": [asdict(c) for c in model.children(node_id)],
        "ancestors": [asdict(a) for a in model.ancestors(node_id)],
        "related_execution": model.related_execution(node_id),
        "related_evidence": {
            "decisions": [asdict(x) for x in dec],
            "sessions": [asdict(x) for x in sess],
        },
        "related_product_docs": [asdict(x) for x in model.related_product_docs(node_id)],
    }
