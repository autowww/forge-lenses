"""Spec Flow board — derive OpenSpec Kanban columns from WBS + openspec/ + Charge."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

import yaml

from lenses.forge_spine import (
    _repo_base,
    parse_charge_banking,
    parse_charge_blockers,
    parse_charge_epics,
)
from lenses.safe_forge_paths import workspace_md_view_link
from lenses.wbs_model import WBS_ID_RE, parse_wbs_markdown

SPEC_FLOW_COLUMNS: tuple[str, ...] = (
    "intent",
    "specify",
    "ready",
    "charged",
    "apply",
    "verify",
    "archived",
)

_COLUMN_LABELS: dict[str, str] = {
    "intent": "Intent",
    "specify": "Specify",
    "ready": "Ready",
    "charged": "Charged",
    "apply": "Apply",
    "verify": "Verify",
    "archived": "Archived",
}

_VALIDATE_CACHE: dict[str, tuple[float, bool]] = {}


def _norm_status(st: str) -> str:
    s = (st or "").strip().lower()
    if s.replace(" ", "") == "inprogress":
        return "in progress"
    return s


def detect_execution_profile(charge_md: str, repo_base: Path) -> str:
    """Return ``epic`` when Active Epics or forge-sdlc OpenSpec schema; else ``spark``."""
    if parse_charge_epics(charge_md):
        return "epic"
    cfg = repo_base / "openspec" / "config.yaml"
    if cfg.is_file():
        try:
            meta = yaml.safe_load(cfg.read_text(encoding="utf-8", errors="replace"))
        except yaml.YAMLError:
            meta = None
        if isinstance(meta, dict):
            schema = str(meta.get("schema") or meta.get("schema_pack") or "").strip()
            if "forge-sdlc" in schema:
                return "epic"
    if "## Active Epics" in charge_md:
        return "epic"
    return "spark"


def _slug_from_cell(cell: str) -> str:
    cell = cell.strip()
    link_m = re.search(r"\]\(([^)]+)\)", cell)
    if link_m:
        parts = link_m.group(1).rstrip("/").split("/")
        return parts[-1] if parts else ""
    return re.sub(r"[`*]", "", cell).strip().split("/")[-1]


def _epic_blocker_ids(charge_md: str) -> set[str]:
    body = charge_md
    ids: set[str] = set()
    for table_rows in _iter_blocker_banking_tables(charge_md):
        if not table_rows:
            continue
        hdr = [h.lower() for h in table_rows[0]]
        joined = " ".join(hdr)
        col = 0
        if "epic" in joined:
            col = next((i for i, h in enumerate(hdr) if "epic" in h), 0)
        elif "spark" in joined:
            col = next((i for i, h in enumerate(hdr) if "spark" in h), 0)
        for row in table_rows[2:]:
            if len(row) <= col:
                continue
            raw = row[col].strip()
            m = WBS_ID_RE.search(raw) or re.search(r"(M\d+E\d+)", raw, re.I)
            if m:
                ids.add(m.group(1).upper())
    return ids


def _iter_blocker_banking_tables(charge_md: str) -> list[list[list[str]]]:
    from lenses.roadmap_outline import iter_gfm_tables

    out: list[list[list[str]]] = []
    for sec in ("## Blockers", "## Banking decisions"):
        if sec not in charge_md:
            continue
        idx = charge_md.index(sec)
        chunk = charge_md[idx : idx + 2000]
        for table in iter_gfm_tables(chunk):
            if len(table) >= 2:
                out.append(table)
    return out


def _epic_banking_ids(charge_md: str) -> set[str]:
    ids: set[str] = set()
    for br in parse_charge_banking(charge_md):
        sid = str(br.get("spark_id") or "").strip()
        if sid and re.match(r"^M\d+E\d+$", sid, re.I):
            ids.add(sid.upper())
    for br in parse_charge_blockers(charge_md):
        sid = str(br.get("spark_id") or "").strip()
        if sid and re.match(r"^M\d+E\d+$", sid, re.I):
            ids.add(sid.upper())
    return ids


def scan_openspec_changes(repo_base: Path) -> dict[str, dict[str, Any]]:
    """Map change slug → {path, archived, proposal_epic_id, validate_ok}."""
    out: dict[str, dict[str, Any]] = {}
    changes_root = repo_base / "openspec" / "changes"
    if not changes_root.is_dir():
        return out

    def _scan_dir(base: Path, *, archived: bool) -> None:
        if not base.is_dir():
            return
        for child in sorted(base.iterdir()):
            if not child.is_dir() or child.name.startswith("."):
                continue
            slug = child.name
            proposal = child / "proposal.md"
            epic_id = ""
            l4_hold = False
            if proposal.is_file():
                text = proposal.read_text(encoding="utf-8", errors="replace")
                m = re.search(r"^##\s+WBS Epic ID\s*\n+\s*(\S+)", text, re.M | re.I)
                if m:
                    epic_id = m.group(1).strip().upper()
                if re.search(r"L4\.2|cross-repo", text, re.I):
                    l4_hold = True
            validate_ok = _openspec_validate_ok(repo_base, slug, child)
            out[slug] = {
                "slug": slug,
                "path": str(child.relative_to(repo_base)).replace("\\", "/"),
                "archived": archived,
                "proposal_epic_id": epic_id,
                "l4_hold": l4_hold,
                "validate_ok": validate_ok,
            }

    _scan_dir(changes_root, archived=False)
    _scan_dir(changes_root / "archive", archived=True)
    return out


def _openspec_validate_ok(repo_base: Path, slug: str, change_dir: Path) -> bool:
    key = str(change_dir.resolve())
    mtime = change_dir.stat().st_mtime
    cached = _VALIDATE_CACHE.get(key)
    if cached and cached[0] == mtime:
        return cached[1]
    ok = False
    try:
        proc = subprocess.run(
            ["openspec", "validate", slug, "--strict"],
            cwd=str(repo_base),
            capture_output=True,
            text=True,
            timeout=8,
        )
        ok = proc.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        spec_files = list(change_dir.glob("specs/**/*.md"))
        ok = bool(spec_files) and (change_dir / "proposal.md").is_file()
    _VALIDATE_CACHE[key] = (mtime, ok)
    return ok


def match_change_to_epic(
    epic_id: str,
    changes: dict[str, dict[str, Any]],
    charge_rows: list[dict[str, Any]],
) -> str | None:
    """Resolve OpenSpec change slug for a WBS Epic id."""
    eid = epic_id.upper()
    for slug, meta in changes.items():
        if str(meta.get("proposal_epic_id") or "").upper() == eid:
            return slug
    for row in charge_rows:
        if str(row.get("epic_id") or "").upper() == eid:
            cs = str(row.get("change_slug") or "").strip()
            if cs:
                return cs
    e_lower = eid.lower()
    for slug in changes:
        if e_lower in slug.lower() or slug.lower().endswith(e_lower.replace("m", "m", 1)):
            return slug
    return None


def derive_column(
    *,
    epic_id: str,
    change_slug: str | None,
    changes: dict[str, dict[str, Any]],
    charge_by_epic: dict[str, dict[str, Any]],
) -> str:
    """Return one of SPEC_FLOW_COLUMNS for an Epic."""
    meta = changes.get(change_slug or "") if change_slug else None
    if change_slug and meta and meta.get("archived"):
        return "archived"
    for slug, m in changes.items():
        if m.get("archived") and str(m.get("proposal_epic_id") or "").upper() == epic_id.upper():
            return "archived"

    crow = charge_by_epic.get(epic_id.upper())
    if crow:
        st = _norm_status(str(crow.get("status") or ""))
        if st == "planned":
            return "charged"
        if st == "in progress":
            return "apply"
        if st == "done":
            return "verify"
        return "charged"

    if not change_slug or not meta:
        return "intent"

    if meta.get("validate_ok"):
        return "ready"
    return "specify"


def build_epic_spec_board_payload(
    workspace_root: Path,
    *,
    repo_hint: str,
    wbs_rel: str,
    roadmap_rel: str | None = None,
) -> dict[str, Any]:
    wr = workspace_root.resolve()
    wbs_path = wr / wbs_rel.replace("\\", "/").strip("/")
    if not wbs_path.is_file():
        return {"ok": False, "error": "wbs_not_found", "wbs_rel": wbs_rel}

    base = _repo_base(wr, repo_hint)
    charge_path = base / "forge" / "charge.md"
    charge_md = charge_path.read_text(encoding="utf-8", errors="replace") if charge_path.is_file() else ""
    profile = detect_execution_profile(charge_md, base)

    columns = [{"id": c, "label": _COLUMN_LABELS[c]} for c in SPEC_FLOW_COLUMNS]
    if profile != "epic":
        return {
            "ok": True,
            "profile": profile,
            "repo_hint": repo_hint,
            "wbs_rel": wbs_rel,
            "roadmap_rel": roadmap_rel or "",
            "columns": columns,
            "cards": [],
        }

    wbs_text = wbs_path.read_text(encoding="utf-8", errors="replace")
    wbs = parse_wbs_markdown(wbs_rel, wbs_text)
    charge_rows = parse_charge_epics(charge_md)
    charge_by_epic = {str(r["epic_id"]).upper(): r for r in charge_rows}
    changes = scan_openspec_changes(base)
    blocked_ids = _epic_blocker_ids(charge_md)
    banked_ids = _epic_banking_ids(charge_md)

    cards: list[dict[str, Any]] = []
    for eid, title, _theme in wbs.epics:
        slug = match_change_to_epic(eid, changes, charge_rows)
        col = derive_column(
            epic_id=eid,
            change_slug=slug,
            changes=changes,
            charge_by_epic=charge_by_epic,
        )
        meta = changes.get(slug or "") if slug else {}
        crow = charge_by_epic.get(eid.upper(), {})
        overlays: list[str] = []
        if eid.upper() in blocked_ids:
            overlays.append("blocked")
        if eid.upper() in banked_ids:
            overlays.append("banked")
        if meta.get("l4_hold"):
            overlays.append("l4_hold")
        wiki = _dual_wiki_overlay(wr, base, slug, changes, repo_hint)
        if wiki.get("wiki_stale"):
            overlays.append("wiki_stale")

        change_path = ""
        if slug and meta:
            change_path = str(meta.get("path") or "")

        cards.append(
            {
                "epic_id": eid,
                "title": title or eid,
                "column": col,
                "change_slug": slug or "",
                "change_path": change_path,
                "charge_status": _norm_status(str(crow.get("status") or "")),
                "actor": str(crow.get("actor") or ""),
                "validate_ok": bool(meta.get("validate_ok")) if meta else False,
                "overlays": overlays,
                "plan_href": f"/plan?wbs_p={wbs_rel}&repo={repo_hint}&id={eid}&tab=spec-board",
            }
        )

    charge_rel = ""
    if charge_path.is_file():
        try:
            charge_rel = str(charge_path.relative_to(wr)).replace("\\", "/")
        except ValueError:
            charge_rel = "forge/charge.md"

    return {
        "ok": True,
        "profile": profile,
        "repo_hint": repo_hint,
        "wbs_rel": wbs_rel,
        "roadmap_rel": roadmap_rel or "",
        "columns": columns,
        "cards": cards,
        "charge": {
            "path": charge_rel,
            "view_href": workspace_md_view_link(charge_rel) if charge_rel else "",
        },
    }


def _dual_wiki_overlay(
    workspace_root: Path,
    repo_base: Path,
    slug: str | None,
    changes: dict[str, dict[str, Any]],
    repo_hint: str,
) -> dict[str, Any]:
    """Return ``{ wiki_stale: bool }`` when declared handbook sides are stale; skip absent shells."""
    if not slug:
        return {"wiki_stale": False}
    meta = changes.get(slug, {})
    change_dir = repo_base / str(meta.get("path") or f"openspec/changes/{slug}")
    proposal_path = change_dir / "proposal.md"
    if not proposal_path.is_file():
        return {"wiki_stale": False}
    from lenses.dual_wiki import freshness

    proposal_md = proposal_path.read_text(encoding="utf-8", errors="replace")
    fr = freshness(
        workspace_root,
        repo_base=repo_base,
        proposal_md=proposal_md,
        repo_hint=repo_hint,
    )
    sides = fr.get("sides") or []
    checked = [s for s in sides if not s.get("skipped")]
    if not checked:
        return {"wiki_stale": False}
    return {"wiki_stale": bool(fr.get("stale"))}


def build_epic_hub_payload(
    workspace_root: Path,
    *,
    repo_hint: str,
    wbs_rel: str,
    epic_id: str,
    roadmap_rel: str | None = None,
) -> dict[str, Any]:
    wr = workspace_root.resolve()
    eid = epic_id.strip().upper()
    if not re.match(r"^M\d+E\d+$", eid):
        return {"ok": False, "error": "invalid_epic_id"}

    base = _repo_base(wr, repo_hint)
    wbs_path = wr / wbs_rel.replace("\\", "/").strip("/")
    if not wbs_path.is_file():
        return {"ok": False, "error": "wbs_not_found"}

    charge_path = base / "forge" / "charge.md"
    charge_md = charge_path.read_text(encoding="utf-8", errors="replace") if charge_path.is_file() else ""
    charge_rows = parse_charge_epics(charge_md)
    changes = scan_openspec_changes(base)
    slug = match_change_to_epic(eid, changes, charge_rows)
    if not slug:
        wbs = parse_wbs_markdown(wbs_rel, wbs_path.read_text(encoding="utf-8", errors="replace"))
        epic_known = any(x[0].upper() == eid for x in wbs.epics)
        if not epic_known:
            return {"ok": False, "error": "epic_not_found"}
        return {
            "ok": True,
            "epic_id": eid,
            "change_slug": "",
            "column": "intent",
            "proposal_excerpt": "",
            "spec_excerpt": "",
            "validate_ok": False,
            "validate_summary": "No OpenSpec change folder yet — scaffold from Intent column.",
            "charge_row": None,
            "size_gate": {
                "has_proposal": False,
                "has_spec": False,
                "validate_strict_green": False,
                "l4_hold": False,
                "wiki_stale": False,
            },
            "dual_wiki": {
                "stale": False,
                "sides": [],
                "reasons": [],
                "refresh_allowed": True,
            },
        }

    meta = changes.get(slug, {})
    change_dir = base / str(meta.get("path") or f"openspec/changes/{slug}")
    proposal_excerpt = _read_excerpt(change_dir / "proposal.md", 4000)
    spec_excerpt = _read_first_spec_excerpt(change_dir, 6000)
    validate_ok = bool(meta.get("validate_ok"))
    crow = next((r for r in charge_rows if str(r.get("epic_id")).upper() == eid), None)
    col = derive_column(
        epic_id=eid,
        change_slug=slug,
        changes=changes,
        charge_by_epic={str(r["epic_id"]).upper(): r for r in charge_rows},
    )
    proposal_full = (change_dir / "proposal.md").read_text(encoding="utf-8", errors="replace")
    from lenses.dual_wiki import dual_wiki_hub_payload

    dual_wiki = dual_wiki_hub_payload(
        wr,
        repo_base=base,
        proposal_md=proposal_full,
        repo_hint=repo_hint,
    )

    return {
        "ok": True,
        "epic_id": eid,
        "change_slug": slug,
        "change_path": str(meta.get("path") or ""),
        "column": col,
        "proposal_excerpt": proposal_excerpt,
        "spec_excerpt": spec_excerpt,
        "validate_ok": validate_ok,
        "validate_summary": "Strict validate green." if validate_ok else "Run `openspec validate --strict` before Ready.",
        "charge_row": crow,
        "size_gate": {
            "has_proposal": (change_dir / "proposal.md").is_file(),
            "has_spec": bool(list(change_dir.glob("specs/**/*.md"))),
            "validate_strict_green": validate_ok,
            "l4_hold": bool(meta.get("l4_hold")),
            "wiki_stale": bool(dual_wiki.get("stale")),
        },
        "dual_wiki": dual_wiki,
        "repo_hint": repo_hint,
        "wbs_rel": wbs_rel,
        "roadmap_rel": roadmap_rel or "",
    }


def _read_excerpt(path: Path, limit: int) -> str:
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[:limit] + ("…" if len(text) > limit else "")


def _read_first_spec_excerpt(change_dir: Path, limit: int) -> str:
    specs = sorted(change_dir.glob("specs/**/*.md"))
    if not specs:
        return ""
    text = specs[0].read_text(encoding="utf-8", errors="replace")
    return text[:limit] + ("…" if len(text) > limit else "")


def apply_epic_spec_transition(
    workspace_root: Path,
    *,
    repo_hint: str,
    wbs_rel: str,
    epic_id: str,
    to_column: str,
    change_slug: str | None = None,
    actor: str = "engineering",
) -> dict[str, Any]:
    """Mutate repo files for a Spec Flow drag. Returns {ok, error?, column?}."""
    from lenses.charge_mutate import (
        archive_openspec_change,
        remove_epic_from_charge,
        scaffold_openspec_change,
        set_epic_charge_status,
        upsert_epic_on_charge,
    )

    wr = workspace_root.resolve()
    base = _repo_base(wr, repo_hint)
    eid = epic_id.strip().upper()
    to_col = to_column.strip().lower()
    if to_col not in SPEC_FLOW_COLUMNS:
        return {"ok": False, "error": "invalid_column", "detail": to_col}

    charge_path = base / "forge" / "charge.md"
    if not charge_path.is_file():
        return {"ok": False, "error": "charge_missing"}

    charge_md = charge_path.read_text(encoding="utf-8", errors="replace")
    charge_rows = parse_charge_epics(charge_md)
    changes = scan_openspec_changes(base)
    slug = (change_slug or "").strip() or match_change_to_epic(eid, changes, charge_rows) or ""
    charge_by = {str(r["epic_id"]).upper(): r for r in charge_rows}
    from_col = derive_column(
        epic_id=eid,
        change_slug=slug or None,
        changes=changes,
        charge_by_epic=charge_by,
    )

    if from_col == to_col and to_col != "ready":
        return {"ok": True, "column": to_col, "epic_id": eid, "noop": True}

    if to_col == "ready" and from_col in ("specify", "intent", "ready"):
        meta = changes.get(slug, {})
        if not meta.get("validate_ok"):
            return {
                "ok": False,
                "error": "validate_not_green",
                "detail": "Specify→Ready requires openspec validate --strict green.",
            }
        change_dir = base / str(meta.get("path") or f"openspec/changes/{slug}")
        proposal_md = ""
        if (change_dir / "proposal.md").is_file():
            proposal_md = (change_dir / "proposal.md").read_text(encoding="utf-8", errors="replace")
        from lenses.dual_wiki import freshness

        fr = freshness(wr, repo_base=base, proposal_md=proposal_md, repo_hint=repo_hint)
        sides = fr.get("sides") or []
        checked = [s for s in sides if not s.get("skipped")]
        if checked and fr.get("stale"):
            return {
                "ok": False,
                "error": "wiki_stale",
                "detail": "Specify→Ready blocked: local handbook HTML is stale. POST dual-wiki-refresh.",
                "reasons": (fr.get("reasons") or [])[:8],
            }
        return {"ok": True, "column": "ready", "epic_id": eid, "noop": True}

    # Specify → Ready: computed only (handled above via to_col == ready)
    if from_col == "specify" and to_col == "ready":
        return {"ok": True, "column": "ready", "epic_id": eid, "noop": True}

    if from_col == "intent" and to_col == "specify":
        if not slug:
            slug = re.sub(r"^M\d+E", "e", eid, flags=re.I).lower().replace("e", "epic-", 1)
            slug = f"epic-{eid.lower()}"
        scaffold_openspec_change(base, slug=slug, epic_id=eid)
        return {"ok": True, "column": "specify", "epic_id": eid, "change_slug": slug}

    status_map = {
        ("ready", "charged"): ("planned", "upsert"),
        ("charged", "apply"): ("in progress", "status"),
        ("apply", "verify"): ("done", "status"),
        ("charged", "ready"): ("", "remove"),
        ("apply", "charged"): ("planned", "status"),
        ("verify", "apply"): ("in progress", "status"),
    }
    key = (from_col, to_col)
    if key == ("verify", "archived"):
        if slug:
            archive_openspec_change(base, slug)
        remove_epic_from_charge(charge_path, eid)
        return {"ok": True, "column": "archived", "epic_id": eid}

    if key in status_map:
        st, op = status_map[key]
        if op == "remove":
            remove_epic_from_charge(charge_path, eid)
        elif op == "upsert":
            upsert_epic_on_charge(
                charge_path,
                epic_id=eid,
                change_slug=slug,
                status=st,
                actor=actor,
                wbs_rel=wbs_rel,
            )
        else:
            set_epic_charge_status(charge_path, eid, st)
        return {"ok": True, "column": to_col, "epic_id": eid}

    return {
        "ok": False,
        "error": "transition_forbidden",
        "detail": f"Cannot move from {from_col} to {to_col}.",
    }


def run_dual_wiki_refresh(
    workspace_root: Path,
    *,
    repo_hint: str,
    wbs_rel: str,
    epic_id: str,
    change_slug: str | None = None,
) -> dict[str, Any]:
    """Run local handbook rebuild script for an Epic change (no Firebase)."""
    wr = workspace_root.resolve()
    base = _repo_base(wr, repo_hint)
    eid = epic_id.strip().upper()
    charge_path = base / "forge" / "charge.md"
    charge_md = charge_path.read_text(encoding="utf-8", errors="replace") if charge_path.is_file() else ""
    charge_rows = parse_charge_epics(charge_md)
    changes = scan_openspec_changes(base)
    slug = (change_slug or "").strip() or match_change_to_epic(eid, changes, charge_rows) or ""
    if not slug:
        return {"ok": False, "error": "change_not_found", "epic_id": eid}

    script = wr / "scripts" / "refresh-dual-wiki.sh"
    if not script.is_file():
        fl_repo = Path(__file__).resolve().parent.parent
        repo_script = fl_repo / "scripts" / "refresh-dual-wiki.sh"
        if repo_script.is_file():
            script = repo_script
    if not script.is_file():
        alt = Path.home() / "Code" / "scripts" / "refresh-dual-wiki.sh"
        script = alt if alt.is_file() else script
    if not script.is_file():
        return {"ok": False, "error": "refresh_script_missing"}

    argv = [str(script), "--repo", repo_hint, "--change", slug]
    try:
        proc = subprocess.run(
            argv,
            cwd=str(wr),
            capture_output=True,
            text=True,
            timeout=1800,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "refresh_timeout", "change_slug": slug}
    except OSError as exc:
        return {"ok": False, "error": "refresh_failed", "detail": str(exc), "change_slug": slug}

    ok = proc.returncode == 0
    return {
        "ok": ok,
        "epic_id": eid,
        "change_slug": slug,
        "returncode": proc.returncode,
        "stdout": (proc.stdout or "")[-4000:],
        "stderr": (proc.stderr or "")[-2000:],
        "error": None if ok else "refresh_failed",
    }
