"""HTTP client for Forge Fleet — multi-node selection, submit Docker argv jobs, poll to completion."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from lenses.fleet_settings_store import fleet_env_override_active, fleet_nodes_for_client


def is_fleet_health_body(body: Any) -> bool:
    """True when JSON looks like Forge Fleet ``GET /v1/health``."""
    if not isinstance(body, dict):
        return False
    return str(body.get("service") or "").strip().lower() == "forge-fleet"


def fleet_configured(workspace_root: Path) -> bool:
    nodes = fleet_nodes_for_client(workspace_root)
    return any(str(n.get("base_url") or "").strip() for n in nodes if n.get("enabled", True))


def _req(
    method: str,
    url: str,
    *,
    bearer: str,
    body: dict[str, Any] | None = None,
    timeout_s: float = 60.0,
) -> tuple[int, dict[str, Any]]:
    data = None
    headers = {"Accept": "application/json"}
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    if body is not None:
        raw = json.dumps(body).encode("utf-8")
        data = raw
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            code = int(getattr(resp, "status", 200) or 200)
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", errors="replace") if e.fp else ""
        code = int(e.code or 500)
    except urllib.error.URLError as e:
        return 0, {"ok": False, "error": "network", "detail": str(e.reason or e)[:800]}
    try:
        parsed = json.loads(text) if text.strip() else {}
    except json.JSONDecodeError:
        parsed = {"raw": text[:4000]}
    if not isinstance(parsed, dict):
        parsed = {"raw": str(parsed)}
    return code, parsed


def get_job_snapshot(fleet_base: str, fleet_token: str, job_id: str, *, timeout_s: float = 20.0) -> dict[str, Any]:
    """GET ``/v1/jobs/{id}`` — used for live status while the Lenses request is blocked on ``wait_for_job``."""
    base = fleet_base.strip().rstrip("/")
    jid = str(job_id or "").strip()
    if not base or not jid:
        return {"ok": False, "error": "missing_base_or_job_id"}
    code, body = _req("GET", f"{base}/v1/jobs/{jid}", bearer=fleet_token or "", timeout_s=timeout_s)
    out: dict[str, Any] = {"ok": code < 400, "http_status": code}
    if isinstance(body, dict):
        for k in ("status", "stdout", "stderr", "exit_code", "container_id", "id"):
            if k in body:
                out[k] = body[k]
    return out


def probe_node_health(base: str, token: str, *, timeout_s: float = 8.0) -> dict[str, Any]:
    base = base.strip().rstrip("/")
    code, body = _req("GET", f"{base}/v1/health", bearer=token, timeout_s=timeout_s)
    fleet_body = body if isinstance(body, dict) else {}
    ok = code < 400 and bool(fleet_body.get("ok", True)) and is_fleet_health_body(fleet_body)
    host = fleet_body.get("host") if isinstance(fleet_body.get("host"), dict) else {}
    cpu = host.get("cpu_usage_pct")
    mem = host.get("memory_used_pct")
    return {
        "ok": ok,
        "http_status": code,
        "base_url": base,
        "cpu_usage_pct": cpu,
        "memory_used_pct": mem,
        "fleet": fleet_body,
    }


def fetch_admin_snapshot(base: str, token: str, *, timeout_s: float = 12.0) -> dict[str, Any]:
    """GET ``/v1/admin/snapshot`` (auth required on most Fleet installs)."""
    base = base.strip().rstrip("/")
    code, body = _req("GET", f"{base}/v1/admin/snapshot", bearer=token, timeout_s=timeout_s)
    return {"ok": code < 400 and isinstance(body, dict) and body.get("ok") is True, "http_status": code, "snapshot": body}


def fetch_admin_snapshot_host(base: str, token: str, *, timeout_s: float = 12.0) -> dict[str, Any] | None:
    """Parsed ``host`` object from a successful admin snapshot, or ``None``."""
    r = fetch_admin_snapshot(base, token, timeout_s=timeout_s)
    if not r.get("ok"):
        return None
    snap = r.get("snapshot") if isinstance(r.get("snapshot"), dict) else {}
    h = snap.get("host")
    return h if isinstance(h, dict) else None


def studio_fleet_status(*, stored_health: dict[str, Any], anon_health: dict[str, Any]) -> str:
    """
    ``connected`` — health OK with stored credentials.
    ``online`` — anonymous health OK but stored probe did not succeed (unusual).
    ``needs_token`` — HTTP reachable, likely Fleet, but not authenticated.
    ``offline`` — no Fleet health.
    """
    st_ok = bool(stored_health.get("ok")) and is_fleet_health_body(stored_health.get("fleet") or {})
    if st_ok:
        return "connected"
    an = anon_health.get("fleet") if isinstance(anon_health.get("fleet"), dict) else {}
    if bool(anon_health.get("ok")) and is_fleet_health_body(an):
        return "online"
    if int(anon_health.get("http_status") or 0) == 401 or int(stored_health.get("http_status") or 0) == 401:
        return "needs_token"
    return "offline"


def _node_within_limits(node: dict[str, Any], health: dict[str, Any]) -> bool:
    max_cpu = node.get("max_cpu_percent")
    max_mem = node.get("max_memory_percent")
    cpu = health.get("cpu_usage_pct")
    mem = health.get("memory_used_pct")
    if max_cpu is not None and cpu is not None:
        try:
            if float(cpu) > float(max_cpu):
                return False
        except (TypeError, ValueError):
            pass
    if max_mem is not None and mem is not None:
        try:
            if float(mem) > float(max_mem):
                return False
        except (TypeError, ValueError):
            pass
    return True


def select_fleet_node_and_rejections(
    workspace_root: Path,
) -> tuple[tuple[str, str, dict[str, Any]] | None, list[dict[str, Any]]]:
    """
    Pick the first **enabled** node (by ascending ``priority``) that responds healthy
    and is within optional CPU / memory ceilings. Returns ``(None, rejections)`` when none qualify.
    """
    nodes = fleet_nodes_for_client(workspace_root)
    candidates: list[dict[str, Any]] = []
    for n in nodes:
        if not isinstance(n, dict):
            continue
        if not n.get("enabled", True):
            continue
        base = str(n.get("base_url") or "").strip().rstrip("/")
        if not base:
            continue
        tok = str(n.get("bearer_token") or "").strip()
        candidates.append({**n, "base_url": base, "bearer_token": tok})
    candidates.sort(key=lambda x: int(x.get("priority") or 100))

    errors: list[dict[str, Any]] = []
    for node in candidates:
        base = node["base_url"]
        tok = node["bearer_token"]
        h = probe_node_health(base, tok, timeout_s=8.0)
        if not h.get("ok"):
            errors.append({"id": node.get("id"), "base_url": base, "reason": "unhealthy", "detail": h})
            continue
        if not _node_within_limits(node, h):
            errors.append(
                {
                    "id": node.get("id"),
                    "base_url": base,
                    "reason": "over_limits",
                    "cpu_usage_pct": h.get("cpu_usage_pct"),
                    "memory_used_pct": h.get("memory_used_pct"),
                    "max_cpu_percent": node.get("max_cpu_percent"),
                    "max_memory_percent": node.get("max_memory_percent"),
                }
            )
            continue
        meta = {"node_id": node.get("id"), "health": h}
        return (base, tok, meta), errors
    return None, errors


def select_fleet_node(workspace_root: Path) -> tuple[str, str, dict[str, Any]] | None:
    """Pick the first eligible Fleet node, or ``None`` if none respond healthy within limits."""
    picked, _ = select_fleet_node_and_rejections(workspace_root)
    return picked


def _probe_stdout_json(stdout: str) -> dict[str, Any] | None:
    raw = (stdout or "").strip()
    if not raw:
        return None
    lines = [ln for ln in raw.splitlines() if ln.strip()]
    if not lines:
        return None
    try:
        o = json.loads(lines[-1])
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def run_test_fleet_batch(
    workspace_root: Path,
    *,
    count: int = 5,
    max_wait_s: float = 150.0,
    poll_s: float = 0.35,
) -> dict[str, Any]:
    """
    Pick an eligible Fleet node, POST ``/v1/admin/test-fleet``, poll job rows until terminal, return samples.

    Used by Lenses Studio (``POST /api/fleet/test-fleet``) so the browser never holds Fleet bearer tokens.
    """
    terminal = frozenset({"completed", "failed", "cancelled"})
    picked, rejections = select_fleet_node_and_rejections(workspace_root)
    if picked is None:
        out: dict[str, Any] = {"ok": False, "error": "fleet_not_configured_or_no_eligible_node"}
        if fleet_env_override_active():
            out["hint"] = (
                "LENSES_FLEET_URL is set but that endpoint did not pass health (URL, token, or Fleet down). "
                "Unset the env vars to use saved Studio Fleet settings instead."
            )
        elif not fleet_configured(workspace_root):
            out["hint"] = (
                "No Fleet base URL is saved for this workspace. Set Base URL on the Localhost tab and click Save "
                "(writes .lenses-local/fleet-settings.json)."
            )
        else:
            out["hint"] = (
                "Saved nodes did not pass GET /v1/health (wrong port is common: user install often listens on "
                "127.0.0.1:18766, not :18765), or bearer is missing/wrong, or Fleet is stopped. "
                "Use Refresh status on the Fleet page and fix rejections below."
            )
        if rejections:
            out["rejections"] = rejections
        return out
    base, token, pick_meta = picked
    n = max(1, min(int(count), 20))
    code, body = _req(
        "POST",
        f"{base}/v1/admin/test-fleet",
        bearer=token,
        body={"count": n},
        timeout_s=90.0,
    )
    if code == 404:
        return {
            "ok": False,
            "error": "fleet_test_fleet_unsupported",
            "detail": "Fleet server has no POST /v1/admin/test-fleet — upgrade forge-fleet.",
            "fleet_endpoint": base,
        }
    if code >= 400 or not isinstance(body, dict):
        return {
            "ok": False,
            "error": "fleet_test_fleet_submit_failed",
            "http_status": code,
            "detail": body if isinstance(body, dict) else str(body)[:800],
            "fleet_endpoint": base,
        }
    if not body.get("ok"):
        return {"ok": False, "error": "fleet_test_fleet_rejected", "detail": body, "fleet_endpoint": base}
    job_ids = [str(x).strip() for x in (body.get("job_ids") or []) if str(x).strip()]
    batch_id = str(body.get("batch_id") or "")
    lenses_hint = bool(body.get("lenses_attention"))
    deadline = time.monotonic() + max_wait_s
    snaps: dict[str, dict[str, Any]] = {}
    completed = False
    while time.monotonic() < deadline:
        for jid in job_ids:
            st0 = str((snaps.get(jid) or {}).get("status") or "").lower()
            if st0 not in terminal:
                c2, b2 = _req("GET", f"{base}/v1/jobs/{jid}", bearer=token, timeout_s=45.0)
                if c2 < 400 and isinstance(b2, dict):
                    snaps[jid] = b2
        if (
            len(job_ids) > 0
            and len(snaps) == len(job_ids)
            and all(str((snaps[j] or {}).get("status") or "").lower() in terminal for j in job_ids)
        ):
            completed = True
            break
        time.sleep(poll_s)
    if not completed:
        return {
            "ok": False,
            "error": "fleet_test_fleet_timeout",
            "batch_id": batch_id,
            "fleet_endpoint": base,
            "job_ids": job_ids,
            "partial_statuses": {j: (snaps.get(j) or {}).get("status") for j in job_ids},
        }
    samples: list[dict[str, Any]] = []
    for jid in job_ids:
        snap = snaps.get(jid) or {}
        probe = _probe_stdout_json(str(snap.get("stdout") or ""))
        stderr = str(snap.get("stderr") or "")
        row: dict[str, Any] = {
            "job_id": jid,
            "status": snap.get("status"),
            "exit_code": snap.get("exit_code"),
            "cpu_usage_pct": probe.get("cpu_usage_pct") if probe else None,
            "slot": probe.get("slot") if probe else None,
        }
        if probe and probe.get("ok") is False:
            row["probe_error"] = probe.get("error")
            row["probe_error_type"] = probe.get("error_type")
        if stderr.strip():
            row["stderr_preview"] = stderr.strip()[:4000]
        samples.append(row)
    return {
        "ok": True,
        "batch_id": batch_id,
        "count": len(job_ids),
        "fleet_endpoint": base,
        "node_pick": pick_meta,
        "lenses_attention_expected": lenses_hint,
        "samples": samples,
    }


def submit_docker_argv_job(
    workspace_root: Path,
    *,
    argv: list[str],
    session_id: str,
    meta: dict[str, Any] | None = None,
) -> tuple[str, str, str]:
    picked = select_fleet_node(workspace_root)
    if picked is None:
        raise RuntimeError("fleet_not_configured_or_no_eligible_node")
    base, token, pick_meta = picked
    url = f"{base}/v1/jobs"
    m = dict(meta or {})
    m.update(pick_meta)
    code, body = _req(
        "POST",
        url,
        bearer=token,
        body={"kind": "docker_argv", "argv": argv, "session_id": session_id, "meta": m},
        timeout_s=120.0,
    )
    if code >= 400:
        raise RuntimeError(f"fleet_submit_failed:{code}:{body.get('error', body)}")
    jid = str(body.get("id") or "").strip()
    if not jid:
        raise RuntimeError("fleet_submit_missing_id")
    return jid, base, token


def wait_for_job(
    workspace_root: Path,
    job_id: str,
    *,
    fleet_base: str | None = None,
    fleet_token: str | None = None,
    poll_s: float = 0.4,
    max_wait_s: float = 3700.0,
) -> dict[str, Any]:
    if fleet_base:
        base = fleet_base.strip().rstrip("/")
        token = fleet_token if fleet_token is not None else ""
    else:
        picked = select_fleet_node(workspace_root)
        if picked is None:
            raise RuntimeError("fleet_poll_no_node")
        base, token, _ = picked
    deadline = time.monotonic() + max_wait_s
    url = f"{base}/v1/jobs/{job_id}"
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        code, body = _req("GET", url, bearer=token, timeout_s=60.0)
        if code >= 400:
            raise RuntimeError(f"fleet_poll_failed:{code}:{body}")
        last = body
        st = str(body.get("status") or "").strip().lower()
        if st in ("completed", "failed", "cancelled"):
            return body
        time.sleep(poll_s)
    raise TimeoutError(f"fleet_job_timeout:{job_id}")


def cancel_job(
    workspace_root: Path,
    job_id: str,
    *,
    fleet_base: str | None = None,
    fleet_token: str | None = None,
) -> None:
    if fleet_base:
        base = fleet_base.strip().rstrip("/")
        token = fleet_token if fleet_token is not None else ""
    else:
        picked = select_fleet_node(workspace_root)
        if picked is None:
            return
        base, token, _ = picked
    _req("POST", f"{base}/v1/jobs/{job_id}/cancel", bearer=token, body={}, timeout_s=30.0)


def parse_step_cli_result(job_payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """Extract (http_status, body) from Fleet job result (last JSON line of stdout)."""
    out = str(job_payload.get("stdout") or "")
    lines = [ln for ln in out.strip().splitlines() if ln.strip()]
    if not lines:
        return 500, {"ok": False, "error": "fleet_empty_stdout", "detail": job_payload.get("stderr") or ""}
    try:
        parsed = json.loads(lines[-1])
    except json.JSONDecodeError:
        return 500, {"ok": False, "error": "fleet_bad_json", "detail": lines[-1][:2000]}
    if not isinstance(parsed, dict):
        return 500, {"ok": False, "error": "fleet_invalid_payload"}
    code = int(parsed.get("http_status") or 500)
    body = parsed.get("body")
    if isinstance(body, dict):
        return code, body
    return code, {"ok": False, "error": "invalid_worker_payload"}


def probe_health(workspace_root: Path) -> dict[str, Any]:
    """Probe every configured node (saved list or env override)."""
    nodes = fleet_nodes_for_client(workspace_root)
    if not nodes:
        return {"ok": False, "error": "fleet_not_configured", "env_override": fleet_env_override_active(), "nodes": []}
    rows: list[dict[str, Any]] = []
    for n in nodes:
        if not isinstance(n, dict):
            continue
        if not n.get("enabled", True):
            rows.append(
                {
                    "id": n.get("id"),
                    "base_url": n.get("base_url"),
                    "skipped": True,
                    "reason": "disabled",
                }
            )
            continue
        base = str(n.get("base_url") or "").strip().rstrip("/")
        tok = str(n.get("bearer_token") or "").strip()
        if not base:
            rows.append({"id": n.get("id"), "skipped": True, "reason": "missing_base_url"})
            continue
        h = probe_node_health(base, tok, timeout_s=8.0)
        h_anon = probe_node_health(base, "", timeout_s=8.0)
        st = studio_fleet_status(stored_health=h, anon_health=h_anon)
        within = _node_within_limits(n, h) if h.get("ok") else False
        fb = h.get("fleet") if isinstance(h.get("fleet"), dict) else {}
        ab = h_anon.get("fleet") if isinstance(h_anon.get("fleet"), dict) else {}
        ver = fb.get("version") if isinstance(fb.get("version"), dict) else {}
        if not ver and isinstance(ab.get("version"), dict):
            ver = ab.get("version")
        rows.append(
            {
                "id": n.get("id"),
                "base_url": base,
                "priority": n.get("priority"),
                "max_cpu_percent": n.get("max_cpu_percent"),
                "max_memory_percent": n.get("max_memory_percent"),
                "health": h,
                "health_anonymous": {
                    "http_status": h_anon.get("http_status"),
                    "ok": h_anon.get("ok"),
                },
                "studio_status": st,
                "version": ver,
                "eligible": bool(h.get("ok")) and within,
            }
        )
    any_ok = any(bool(r.get("eligible")) for r in rows)
    rollup = rollup_fleet_nodes(rows)
    try:
        rollup = merge_rollup_with_snapshots(workspace_root, rows)
    except (OSError, RuntimeError, TypeError, ValueError, KeyError):
        pass
    return {
        "ok": any_ok or (len(rows) == 0 and not nodes),
        "env_override": fleet_env_override_active(),
        "nodes": rows,
        "rollup": rollup,
    }


def rollup_fleet_nodes(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Weighted averages for ``connected`` nodes (weight ``1/max(priority,1)``)."""
    connected = [
        r
        for r in rows
        if not r.get("skipped") and r.get("studio_status") == "connected" and isinstance(r.get("health"), dict)
    ]
    if not connected:
        return {
            "connected_count": 0,
            "configured_count": len([r for r in rows if not r.get("skipped")]),
            "weight_sum": 0.0,
            "cpu_usage_pct": None,
            "memory_used_pct": None,
            "loadavg_1m": None,
            "cpus_logical_sum": None,
            "avg_ghz": None,
            "memory_total_gb_sum": None,
        }
    tw = 0.0
    acc_cpu = 0.0
    acc_mem = 0.0
    acc_load = 0.0
    w_cpu = 0.0
    w_mem = 0.0
    w_load = 0.0
    for r in connected:
        try:
            pri = max(int(r.get("priority") or 100), 1)
        except (TypeError, ValueError):
            pri = 100
        w = 1.0 / float(pri)
        tw += w
        h = r.get("health") or {}
        fb = h.get("fleet") if isinstance(h.get("fleet"), dict) else {}
        host = fb.get("host") if isinstance(fb.get("host"), dict) else {}
        cpu = host.get("cpu_usage_pct")
        mem = host.get("memory_used_pct")
        la = host.get("loadavg_1m")
        if isinstance(cpu, (int, float)):
            acc_cpu += w * float(cpu)
            w_cpu += w
        if isinstance(mem, (int, float)):
            acc_mem += w * float(mem)
            w_mem += w
        if isinstance(la, (int, float)):
            acc_load += w * float(la)
            w_load += w
    out: dict[str, Any] = {
        "connected_count": len(connected),
        "configured_count": len([x for x in rows if not x.get("skipped")]),
        "weight_sum": round(tw, 6),
        "cpu_usage_pct": round(acc_cpu / w_cpu, 2) if w_cpu > 0 else None,
        "memory_used_pct": round(acc_mem / w_mem, 2) if w_mem > 0 else None,
        "loadavg_1m": round(acc_load / w_load, 4) if w_load > 0 else None,
        "cpus_logical_sum": None,
        "avg_ghz": None,
        "memory_total_gb_sum": None,
    }
    return out


def describe_fleet_node(workspace_root: Path, node_id: str, *, include_snapshot: bool = True) -> dict[str, Any]:
    """Single-node detail for Studio (optionally includes ``/v1/admin/snapshot``)."""
    nodes = fleet_nodes_for_client(workspace_root)
    target: dict[str, Any] | None = None
    for n in nodes:
        if isinstance(n, dict) and str(n.get("id") or "").strip() == str(node_id or "").strip():
            target = n
            break
    if target is None:
        return {"ok": False, "error": "node_not_found", "node_id": node_id}
    base = str(target.get("base_url") or "").strip().rstrip("/")
    tok = str(target.get("bearer_token") or "").strip()
    if not base:
        return {"ok": False, "error": "missing_base_url", "node_id": node_id}
    h = probe_node_health(base, tok)
    h_anon = probe_node_health(base, "")
    st = studio_fleet_status(stored_health=h, anon_health=h_anon)
    out: dict[str, Any] = {
        "ok": True,
        "node_id": node_id,
        "base_url": base,
        "studio_status": st,
        "health": h,
        "health_anonymous": {"http_status": h_anon.get("http_status"), "ok": h_anon.get("ok")},
    }
    snap_full: dict[str, Any] | None = None
    if include_snapshot and st == "connected":
        snap = fetch_admin_snapshot(base, tok)
        out["snapshot"] = snap
        snap_full = snap.get("snapshot") if isinstance(snap.get("snapshot"), dict) else None
        if isinstance(snap_full, dict):
            host = snap_full.get("host") if isinstance(snap_full.get("host"), dict) else {}
            cpus = host.get("cpus")
            if isinstance(cpus, (int, float)) and int(cpus) > 0:
                ic = int(cpus)
                out["rollup_slice"] = {
                    "cpus": ic,
                    "cpu_ghz_avg": _avg_ghz_from_host(host),
                    "memory_total_gb": _memory_total_gb(host),
                }
    return out


def _memory_total_gb(host: dict[str, Any]) -> float | None:
    mem = host.get("memory") if isinstance(host.get("memory"), dict) else {}
    kb = mem.get("total_kb")
    try:
        if kb is None:
            return None
        return round(float(kb) / 1_000_000.0, 2)
    except (TypeError, ValueError):
        return None


def _avg_ghz_from_host(host: dict[str, Any]) -> float | None:
    """Average CPU GHz from Fleet ``host_stats.snapshot`` (``cpu_freq_mhz_avg``)."""
    mhz = host.get("cpu_freq_mhz_avg")
    if isinstance(mhz, (int, float)) and float(mhz) > 0:
        return round(float(mhz) / 1000.0, 3)
    return None


def merge_rollup_with_snapshots(workspace_root: Path, probe_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Recompute rollup including ``cpus`` / memory from snapshots (best effort)."""
    base_rollup = rollup_fleet_nodes(probe_rows)
    connected_ids = [
        str(r.get("id") or "")
        for r in probe_rows
        if not r.get("skipped") and r.get("studio_status") == "connected" and str(r.get("id") or "")
    ]
    cpus_sum = 0
    ghz_w: list[tuple[float, float]] = []
    mem_gb = 0.0
    for nid in connected_ids:
        d = describe_fleet_node(workspace_root, nid, include_snapshot=True)
        sl = d.get("rollup_slice") if isinstance(d.get("rollup_slice"), dict) else {}
        c = sl.get("cpus")
        if isinstance(c, (int, float)):
            cpus_sum += int(c)
        g = sl.get("cpu_ghz_avg")
        if isinstance(g, (int, float)) and isinstance(c, (int, float)) and float(c) > 0:
            ghz_w.append((float(g), float(c)))
        mg = sl.get("memory_total_gb")
        if isinstance(mg, (int, float)):
            mem_gb += float(mg)
    avg_g: float | None = None
    if ghz_w:
        tw = sum(w for _, w in ghz_w)
        avg_g = round(sum(g * w for g, w in ghz_w) / tw, 3) if tw > 0 else None
    base_rollup["cpus_logical_sum"] = cpus_sum if cpus_sum > 0 else base_rollup.get("cpus_logical_sum")
    base_rollup["avg_ghz"] = avg_g
    base_rollup["memory_total_gb_sum"] = round(mem_gb, 2) if mem_gb > 0 else None
    return base_rollup
