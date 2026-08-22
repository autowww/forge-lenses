"""HTTP handlers for /api/foundry/*."""

from __future__ import annotations

import urllib.parse
from pathlib import Path
from typing import Any, Callable

from lenses.foundry.activity import append_activity, bootstrap_run_activity
from lenses.foundry.feature import foundry_enabled
from lenses.foundry.intake import parse_intake_message
from lenses.foundry.launcher import launch_run_async
from lenses.foundry.payload import capabilities_payload, normalize_run_dir
from lenses.foundry.plan import build_plan
from lenses.foundry.promote import promote_from_run_dir
from lenses.foundry.review import build_review_payload
from lenses.foundry.target_resolve import resolve_foundry_target
from lenses.foundry.store import (
    create_run_record,
    list_runs,
    load_run,
    runs_root,
    save_run,
    touch_run,
)

SendJson = Callable[[int, dict[str, Any]], None]

LENSES_REPO_ROOT = Path(__file__).resolve().parents[2]


def _disabled() -> dict[str, Any]:
    return {"ok": False, "feature_disabled": True}


def _resolve_target(workspace_root: Path, body: dict[str, Any]) -> Path | None:
    repo, _hint = resolve_foundry_target(workspace_root, body)
    return repo


def _run_public(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": True,
        "id": record.get("id"),
        "status": record.get("status"),
        "goal": record.get("goal"),
        "target": record.get("target"),
        "level": record.get("level"),
        "execution_mode": record.get("execution_mode"),
        "project": record.get("project"),
        "phases": record.get("phases") or [],
        "plan": record.get("plan") or {},
        "final_status": record.get("final_status"),
        "assay_ok": record.get("assay_ok"),
        "foundry_run_dir": record.get("foundry_run_dir"),
        "promoted": record.get("promoted"),
        "approved": record.get("approved"),
        "activity": record.get("activity") or [],
        "current_phase": record.get("current_phase"),
        "created_at": record.get("created_at"),
        "updated_at": record.get("updated_at"),
    }


def handle_foundry_get(
    *,
    workspace_root: Path,
    path: str,
    send_json: SendJson,
) -> bool:
    p = path.rstrip("/") or "/"
    if not p.startswith("/api/foundry"):
        return False

    if p == "/api/foundry/enabled":
        send_json(200, {"ok": True, "enabled": foundry_enabled()})
        return True

    if not foundry_enabled():
        send_json(200, _disabled())
        return True

    if p == "/api/foundry/capabilities":
        send_json(200, capabilities_payload())
        return True

    if p == "/api/foundry/runs":
        rows = [_run_public(r) for r in list_runs(workspace_root)]
        send_json(200, {"ok": True, "runs": rows})
        return True

    if p.startswith("/api/foundry/runs/"):
        rid = urllib.parse.unquote(p[len("/api/foundry/runs/") :].strip("/"))
        record = load_run(workspace_root, rid) if rid else None
        if not record:
            send_json(404, {"ok": False, "error": "not_found"})
            return True
        payload = _run_public(record)
        run_dir = str(record.get("foundry_run_dir") or "").strip()
        if run_dir:
            normalized = normalize_run_dir(Path(run_dir))
            payload["phases"] = normalized.get("phases") or payload.get("phases")
            payload["assay"] = normalized.get("assay")
            payload["proof"] = normalized.get("proof")
            live = Path(str(record.get("target") or ""))
            if live.is_dir():
                phases_doc = Path(run_dir) / "machine" / "phases.json"
                phases_raw = None
                if phases_doc.is_file():
                    try:
                        import json as _json

                        phases_raw = (_json.loads(phases_doc.read_text(encoding="utf-8")) or {}).get("phases")
                    except (OSError, ValueError):
                        phases_raw = None
                payload["review"] = build_review_payload(
                    run_dir=Path(run_dir),
                    live_target=live,
                    proof=normalized.get("proof") if isinstance(normalized.get("proof"), dict) else None,
                    promoted=bool(record.get("promoted")),
                    goal=str(record.get("goal") or ""),
                    phases_raw=phases_raw if isinstance(phases_raw, list) else None,
                    plan=record.get("plan") if isinstance(record.get("plan"), dict) else None,
                )
        send_json(200, payload)
        return True

    send_json(404, {"ok": False, "error": "not_found"})
    return True


def handle_foundry_post(
    *,
    workspace_root: Path,
    post_path: str,
    body: dict[str, Any],
    send_json: SendJson,
    may_run_actions: Callable[[str], bool],
    client_ip: str,
) -> bool:
    p = post_path.rstrip("/") or "/"
    if not p.startswith("/api/foundry"):
        return False

    if not foundry_enabled():
        send_json(404, _disabled())
        return True

    if p == "/api/foundry/plan":
        send_json(200, build_plan(body, workspace_root))
        return True

    if p == "/api/foundry/intake":
        msg = str(body.get("message") or body.get("text") or "").strip()
        send_json(200, parse_intake_message(msg, default_project=str(body.get("project") or "")))
        return True

    if p == "/api/foundry/campaigns":
        send_json(
            501,
            {
                "ok": False,
                "error": "not_implemented",
                "reason": "dark_factory_level_not_wired",
            },
        )
        return True

    if p == "/api/foundry/runs":
        if not may_run_actions(client_ip):
            send_json(403, {"ok": False, "error": "allowed_from_loopback_or_lenses_allow_actions"})
            return True
        level = str(body.get("level") or "L1").strip().upper()
        if level != "L1":
            send_json(
                501,
                {
                    "ok": False,
                    "error": "not_implemented",
                    "reason": "dark_factory_level_not_wired",
                },
            )
            return True
        goal = str(body.get("goal") or "").strip()
        target = _resolve_target(workspace_root, body)
        if not goal or target is None or not target.is_dir():
            send_json(400, {"ok": False, "error": "goal_and_target_required"})
            return True
        plan_body = body.get("plan") if isinstance(body.get("plan"), dict) else None
        if plan_body is None:
            plan_body = build_plan({**body, "target": str(target)}, workspace_root)
            if not plan_body.get("ok"):
                send_json(400, plan_body)
                return True
        record = create_run_record(
            goal=goal,
            target=str(target),
            level=level,
            execution_mode=str(body.get("execution_mode") or "draft"),
            project=str(body.get("project") or ""),
            plan=plan_body,
        )
        record = touch_run(record, status="running")
        save_run(workspace_root, record)
        worker = str(body.get("worker") or "fake").strip().lower()
        bootstrap_run_activity(
            workspace_root,
            record["id"],
            goal=goal,
            worker=worker,
            project=str(body.get("project") or ""),
        )

        fixture_raw = str(body.get("fixture") or "").strip()
        fixture = Path(fixture_raw) if fixture_raw else target / "fixtures" / "multiply_fix.json"
        if not fixture.is_file():
            fixture = None
        out_parent = runs_root(workspace_root) / record["id"] / "df-out"
        allowed: tuple[str, ...] | None = None
        verification: tuple[str, ...] | None = None
        units = plan_body.get("units") if isinstance(plan_body.get("units"), list) else []
        if units and isinstance(units[0], dict):
            raw_af = units[0].get("allowed_files")
            if isinstance(raw_af, list) and raw_af:
                allowed = tuple(str(x) for x in raw_af)
            raw_vc = units[0].get("verification_commands")
            if isinstance(raw_vc, list) and raw_vc and all(isinstance(x, str) for x in raw_vc):
                verification = tuple(str(x) for x in raw_vc)

        def on_complete(normalized: dict[str, Any]) -> None:
            rec = load_run(workspace_root, record["id"]) or record
            run_dir = normalized.get("run_dir", "")
            status = "completed" if normalized.get("final_status") == "pass" else "failed"
            rec = touch_run(
                rec,
                status=status,
                foundry_run_dir=run_dir,
                phases=normalized.get("phases") or [],
                final_status=normalized.get("final_status"),
                assay_ok=normalized.get("assay_ok"),
            )
            save_run(workspace_root, rec)
            append_activity(
                workspace_root,
                record["id"],
                text=f"Run finished — {normalized.get('final_status', status)}",
                tone="ok" if status == "completed" else "err",
            )

        def on_error(msg: str) -> None:
            rec = load_run(workspace_root, record["id"]) or record
            rec = touch_run(rec, status="failed", error=msg)
            save_run(workspace_root, rec)
            append_activity(workspace_root, record["id"], text=f"Run failed — {msg[:500]}", tone="err")

        launch_run_async(
            lenses_repo_root=LENSES_REPO_ROOT,
            goal=goal,
            target=target,
            out_parent=out_parent,
            level=level,
            worker=worker,
            fixture=fixture,
            allowed_files=allowed,
            verification_argv=verification,
            workspace_root=workspace_root,
            run_id=record["id"],
            on_complete=on_complete,
            on_error=on_error,
        )
        send_json(201, _run_public(record))
        return True

    if p.startswith("/api/foundry/runs/") and p.endswith("/approve"):
        if not may_run_actions(client_ip):
            send_json(403, {"ok": False, "error": "allowed_from_loopback_or_lenses_allow_actions"})
            return True
        rid = urllib.parse.unquote(p[len("/api/foundry/runs/") : -len("/approve")].strip("/"))
        record = load_run(workspace_root, rid) if rid else None
        if not record:
            send_json(404, {"ok": False, "error": "not_found"})
            return True
        if not bool(body.get("confirm_human_approval")):
            send_json(
                400,
                {
                    "ok": False,
                    "error": "confirm_human_approval_required",
                    "detail": "Set confirm_human_approval:true after explicit human review.",
                },
            )
            return True
        if record.get("status") != "completed" or not record.get("assay_ok"):
            send_json(400, {"ok": False, "error": "run_not_ready_for_promote"})
            return True
        run_dir = Path(str(record.get("foundry_run_dir") or ""))
        live = Path(str(record.get("target") or ""))
        if not run_dir.is_dir() or not live.is_dir():
            send_json(400, {"ok": False, "error": "paths_missing"})
            return True
        pr = promote_from_run_dir(run_dir=run_dir, live_target=live, promote_scope="file")
        if not pr.get("ok"):
            send_json(400, pr)
            return True
        record = touch_run(record, approved=True, promoted=True, promote_result=pr)
        save_run(workspace_root, record)
        send_json(200, {"ok": True, "run": _run_public(record), "promote": pr})
        return True

    send_json(404, {"ok": False, "error": "not_found"})
    return True
