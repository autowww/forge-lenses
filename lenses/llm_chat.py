"""LLM chat orchestration: validation, model resolution, completion transport, analytics."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from lenses.llm_completions import complete_user_message, ollama_daemon_status
from lenses.llm_resolve import effective_provider_for_task, resolve_effective_model
from lenses.llm_settings_store import merged_openai_compat_base_url

# Re-export for serve.py, tests, and callers that imported from llm_chat.
# Max single user message length (chars).
MAX_MESSAGE_CHARS = 32_000


def _env_trim(key: str) -> str:
    return (os.environ.get(key) or "").strip()


def providers_available(workspace_root: Path | None = None) -> dict[str, bool]:
    """Which providers have required env or file keys (booleans only)."""
    if workspace_root is not None:
        from lenses.llm_resolve import providers_with_store

        return providers_with_store(workspace_root)
    base = _env_trim("LENSES_OPENAI_COMPAT_BASE_URL")
    return {
        "anthropic": bool(_env_trim("ANTHROPIC_API_KEY")),
        "openai": bool(_env_trim("OPENAI_API_KEY")),
        "gemini": bool(_env_trim("GOOGLE_API_KEY") or _env_trim("GEMINI_API_KEY")),
        "ollama": bool(_env_trim("OLLAMA_BASE_URL")),
        "openai_compatible": bool(base),
    }


_VALID_PROVIDERS = frozenset(
    ("anthropic", "openai", "gemini", "ollama", "openai_compatible"),
)


def chat(
    provider: str,
    message: str,
    model_override: str | None = None,
    *,
    workspace_root: Path | None = None,
    refine: bool = False,
    studio_task_id: str | None = None,
) -> dict[str, Any]:
    """Run one user message through the configured provider."""
    req_pid = (provider or "").strip().lower()
    if req_pid not in _VALID_PROVIDERS:
        return {"ok": False, "error": "invalid_provider", "detail": req_pid or "(empty)"}
    msg = (message or "").strip()
    if not msg:
        return {"ok": False, "error": "missing_message"}
    if len(msg) > MAX_MESSAGE_CHARS:
        return {
            "ok": False,
            "error": "message_too_long",
            "detail": str(MAX_MESSAGE_CHARS),
        }

    file_keys: dict[str, str] | None = None
    pid = req_pid
    eff_model_override: str | None = model_override
    compat_base: str | None = None
    if workspace_root is not None:
        from lenses.llm_resolve import merged_secret_keys
        from lenses.llm_settings_store import load_raw

        raw = load_raw(workspace_root)
        file_keys = merged_secret_keys(raw)
        ep, em, _privacy_warn = effective_provider_for_task(
            raw,
            studio_task_id,
            req_pid,
            model_override,
            workspace_root=workspace_root,
        )
        pid = (ep or req_pid).strip().lower()
        if pid not in _VALID_PROVIDERS:
            return {"ok": False, "error": "invalid_provider", "detail": ep or "(empty)"}
        eff_model_override = em
        cb = merged_openai_compat_base_url(raw)
        compat_base = cb if cb else None

    resolved_model, _, dbg = resolve_effective_model(
        pid,
        workspace_root=workspace_root,
        model_override=eff_model_override,
        refine=refine,
        user_message=msg,
    )
    eff_model = resolved_model if resolved_model else eff_model_override

    fk = file_keys or {}

    out = complete_user_message(
        pid,
        msg,
        eff_model,
        fk,
        openai_compat_base_url=compat_base if pid == "openai_compatible" else None,
    )

    if (
        not out.get("ok")
        and workspace_root is not None
        and studio_task_id
        and str(raw.get("routing_mode") or "").strip().lower() == "advanced"
    ):
        tr_fb = raw.get("task_routes")
        if isinstance(tr_fb, dict):
            ent_fb = tr_fb.get(str(studio_task_id).strip())
            if isinstance(ent_fb, dict):
                fb_p = str(ent_fb.get("fallback_provider") or "").strip().lower()
                if fb_p in _VALID_PROVIDERS and fb_p != pid:
                    fb_model = str(ent_fb.get("fallback_model") or "").strip() or None
                    fb_resolved, _, fb_dbg = resolve_effective_model(
                        fb_p,
                        workspace_root=workspace_root,
                        model_override=fb_model,
                        refine=refine,
                        user_message=msg,
                    )
                    fb_eff = fb_resolved if fb_resolved else fb_model
                    cb2 = merged_openai_compat_base_url(raw)
                    compat2 = cb2 if cb2 and fb_p == "openai_compatible" else None
                    out = complete_user_message(
                        fb_p,
                        msg,
                        fb_eff,
                        fk,
                        openai_compat_base_url=compat2,
                    )
                    if out.get("ok"):
                        dbg = dict(fb_dbg) if isinstance(fb_dbg, dict) else {}
                        dbg["fallback_from"] = pid
                        pid = fb_p
                        eff_model = fb_eff

    if out.get("ok"):
        rdbg = dict(dbg) if isinstance(dbg, dict) else {}
        if studio_task_id:
            rdbg["studio_task_id"] = studio_task_id
        out["routing"] = rdbg
        if eff_model:
            out["model"] = eff_model

    if workspace_root is not None:
        from lenses.llm_usage_store import record_llm_chat_result

        mid_for_log = out.get("model") if out.get("ok") else None
        if not mid_for_log:
            mid_for_log = eff_model
        rdebug: dict[str, Any] = dict(dbg) if isinstance(dbg, dict) else {}
        rout = out.get("routing")
        if isinstance(rout, dict):
            rdebug = {**rdebug, **rout}
        record_llm_chat_result(
            workspace_root,
            pid,
            ok=bool(out.get("ok")),
            result=out,
            message=msg,
            refine=refine,
            routing_debug=rdebug,
            model_id=str(mid_for_log).strip() if mid_for_log else None,
        )
    return out
