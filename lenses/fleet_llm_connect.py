"""Wire a Fleet-hosted forge-llm gateway into Lenses LLM settings (``openai_compatible``)."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from pathlib import Path

from lenses.llm_settings_store import load_raw as llm_load_raw
from lenses.llm_settings_store import merge_save as llm_merge_save
from lenses.llm_settings_store import merged_openai_compat_base_url
from lenses.llm_settings_store import save_raw as llm_save_raw
from lenses.sandbox import fleet_client as fleet_cli


def _fleet_hostname(base_url: str) -> str | None:
    try:
        u = urlparse(base_url.strip())
        return u.hostname
    except (ValueError, TypeError):
        return None


def connect_forge_llm_to_llm_settings(
    workspace_root: Path,
    body: dict[str, Any],
) -> dict[str, Any]:
    """
    Body keys: ``fleet_node_id`` (required), ``openai_base_url`` (optional),
    ``bearer_token`` (optional, forge-gateway token).
    """
    node_id = str(body.get("fleet_node_id") or "").strip()
    if not node_id:
        return {"ok": False, "error": "missing_fleet_node_id"}
    manual = str(body.get("openai_base_url") or "").strip().rstrip("/")
    bearer_in = str(body.get("bearer_token") or "").strip()

    nodes = fleet_cli.fleet_nodes_for_client(workspace_root)
    target: dict[str, Any] | None = None
    for n in nodes:
        if isinstance(n, dict) and str(n.get("id") or "").strip() == node_id:
            target = n
            break
    if target is None:
        return {"ok": False, "error": "fleet_node_not_found", "fleet_node_id": node_id}

    base = str(target.get("base_url") or "").strip().rstrip("/")
    tok = str(target.get("bearer_token") or "").strip()
    if not base:
        return {"ok": False, "error": "fleet_node_missing_base_url"}

    h = fleet_cli.probe_node_health(base, tok)
    if not h.get("ok"):
        return {"ok": False, "error": "fleet_node_not_connected", "detail": h}

    effective = manual
    if not effective:
        code, fb = fleet_cli._req("GET", f"{base}/v1/services/forge-llm", bearer=tok, timeout_s=20.0)  # noqa: SLF001
        if code >= 400 or not isinstance(fb, dict):
            return {"ok": False, "error": "forge_llm_status_http", "http_status": code}
        if not fb.get("configured"):
            return {"ok": False, "error": "forge_llm_not_configured", "detail": fb}
        gw = fb.get("gateway_publish") if isinstance(fb.get("gateway_publish"), dict) else {}
        hp = gw.get("host_port")
        host = _fleet_hostname(base)
        if not host or not isinstance(hp, int):
            return {
                "ok": False,
                "error": "needs_manual_url",
                "detail": "Could not infer published forge-gateway port from compose ps.",
                "fleet_body": fb,
            }
        effective = f"http://{host}:{int(hp)}"

    prev = merged_openai_compat_base_url(llm_load_raw(workspace_root))
    url_unchanged = bool(prev and prev.rstrip("/") == effective)
    if url_unchanged and not bearer_in:
        return {"ok": True, "unchanged": True, "openai_compatible_base_url": effective}

    incoming: dict[str, Any] = {}
    if not url_unchanged:
        incoming["openai_compatible_base_url"] = effective
    if bearer_in:
        incoming["keys"] = {"openai_compatible": bearer_in}
    merged = llm_merge_save(workspace_root, incoming)
    llm_save_raw(workspace_root, merged)
    return {
        "ok": True,
        "openai_compatible_base_url": effective,
        "unchanged": url_unchanged and not bearer_in,
        "replaced_previous": bool(prev) and not url_unchanged,
        "previous_preview": (prev[:96] + "…") if len(prev) > 96 else prev or None,
    }
