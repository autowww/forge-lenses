"""Persist LLM UI settings under ``<workspace_root>/.lenses-local/llm-settings.json``."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

SETTINGS_FILENAME = "llm-settings.json"
CURRENT_VERSION = 2

_DEFAULT: dict[str, Any] = {
    "version": CURRENT_VERSION,
    "provider": "openai",
    "routing_mode": "single",
    "advanced_ui": False,
    "auto_model": False,
    "adaptive_autoselection": False,
    "tier": "MED",
    "refine_cheaper_steps": 2,
    "keys": {
        "anthropic": "",
        "openai": "",
        "gemini": "",
        "openai_compatible": "",
    },
    "main_models": {
        "anthropic": "claude-3-5-haiku-20241022",
        "openai": "gpt-4o-mini",
        "gemini": "gemini-2.0-flash",
        "ollama": "llama3.2",
        "openai_compatible": "gpt-4o-mini",
    },
    "pools": {
        "anthropic": [],
        "openai": [],
        "gemini": [],
        "ollama": [],
        "openai_compatible": [],
    },
    "classifier_models": {
        "openai": "",
        "gemini": "",
    },
    "task_routes": {},
    "fallback_route": {"provider": "", "model": ""},
    "openai_compatible_base_url": "",
    "custom_provider": {
        "display_name": "",
        "transport": "openai_compatible",
        "auth": "bearer",
    },
    "first_run_wizard_dismissed": False,
}


def migrate_llm_settings_inplace(out: dict[str, Any]) -> None:
    """Backfill routing_mode, task route privacy fields, and wizard flag without dropping keys."""

    def _infer_routing_mode_from_legacy(raw: dict[str, Any]) -> str:
        adv = bool(raw.get("advanced_ui"))
        auto = bool(raw.get("auto_model"))
        if not adv:
            return "single"
        if auto:
            return "smart"
        return "advanced"

    rm = str(out.get("routing_mode") or "").strip().lower()
    if rm not in ("single", "smart", "advanced"):
        out["routing_mode"] = _infer_routing_mode_from_legacy(out)
    tr = out.get("task_routes")
    if isinstance(tr, dict):
        for tid, row in list(tr.items()):
            if not isinstance(row, dict):
                continue
            pr = str(row.get("privacy") or "").strip().lower()
            if pr not in ("local_only", "prefer_local", "cloud_allowed"):
                row["privacy"] = "cloud_allowed"
            row.setdefault("fallback_provider", str(row.get("fallback_provider", "") or "").strip())
            row.setdefault("fallback_model", str(row.get("fallback_model", "") or "").strip())
            ms_raw = row.get("model_stack")
            stack: list[str] = []
            if isinstance(ms_raw, list):
                for x in ms_raw:
                    s = str(x or "").strip()
                    if s:
                        stack.append(s)
            if not stack:
                m0 = str(row.get("model") or "").strip()
                if m0:
                    stack = [m0]
            row["model_stack"] = stack
            row["model"] = stack[0] if stack else str(row.get("model") or "").strip()
            tr[str(tid)] = row
        out["task_routes"] = tr
    out.setdefault("first_run_wizard_dismissed", False)


def _normalize_settings(out: dict[str, Any]) -> None:
    """Fill v2 fields and bump version when loading legacy files."""
    v = int(out.get("version") or 1)
    if v < 2:
        out["version"] = 2
    out.setdefault("routing_mode", "single")
    tr = out.get("task_routes")
    if not isinstance(tr, dict):
        out["task_routes"] = {}
    fr = out.get("fallback_route")
    if not isinstance(fr, dict):
        out["fallback_route"] = {"provider": "", "model": ""}
    else:
        out["fallback_route"] = {
            "provider": str(fr.get("provider", "") or "").strip(),
            "model": str(fr.get("model", "") or "").strip(),
        }
    out.setdefault("openai_compatible_base_url", "")
    # Keys must remain plain strings on disk; reject objects (e.g. masked GET shape) if ever written.
    km = out.get("keys")
    if isinstance(km, dict):
        for kk in ("anthropic", "openai", "gemini", "openai_compatible"):
            if kk not in km:
                continue
            if not isinstance(km.get(kk), str):
                km[kk] = ""
    cp = out.get("custom_provider")
    if not isinstance(cp, dict):
        out["custom_provider"] = json.loads(json.dumps(_DEFAULT["custom_provider"]))
    else:
        d0 = _DEFAULT["custom_provider"]
        if isinstance(d0, dict):
            merged_cp = {**d0, **{str(k): v for k, v in cp.items() if k in d0}}
            out["custom_provider"] = merged_cp
    migrate_llm_settings_inplace(out)


def settings_path(workspace_root: Path) -> Path:
    return workspace_root.resolve() / ".lenses-local" / SETTINGS_FILENAME


def load_raw(workspace_root: Path) -> dict[str, Any]:
    p = settings_path(workspace_root)
    if not p.is_file():
        return json.loads(json.dumps(_DEFAULT))
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return json.loads(json.dumps(_DEFAULT))
    if not isinstance(data, dict):
        return json.loads(json.dumps(_DEFAULT))
    out = json.loads(json.dumps(_DEFAULT))
    for k, v in data.items():
        if k in out:
            out[k] = v
    _normalize_settings(out)
    return out


def save_raw(workspace_root: Path, data: dict[str, Any]) -> None:
    p = settings_path(workspace_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(p.parent, 0o700)
    except OSError:
        pass
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(p)
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass


def _mask_key(k: str) -> str:
    t = (k or "").strip()
    if len(t) <= 8:
        return "" if not t else "********"
    return t[:4] + "…" + t[-4:]


def _env_trim(name: str) -> str:
    return (os.environ.get(name) or "").strip()


def _env_secret_and_hint(pname: str) -> tuple[str, str]:
    """Return (trimmed env secret, UI hint name) for provider keys (matches llm_resolve.merge_key)."""
    if pname == "anthropic":
        return _env_trim("ANTHROPIC_API_KEY"), "ANTHROPIC_API_KEY"
    if pname == "openai":
        return _env_trim("OPENAI_API_KEY"), "OPENAI_API_KEY"
    if pname == "gemini":
        g = _env_trim("GOOGLE_API_KEY")
        if g:
            return g, "GOOGLE_API_KEY"
        g2 = _env_trim("GEMINI_API_KEY")
        if g2:
            return g2, "GEMINI_API_KEY"
        return "", ""
    if pname == "openai_compatible":
        return _env_trim("LENSES_OPENAI_COMPAT_KEY"), "LENSES_OPENAI_COMPAT_KEY"
    return "", ""


def sanitize_for_get(data: dict[str, Any]) -> dict[str, Any]:
    """Return a copy safe for JSON GET (masked keys, booleans for presence).

    ``set`` is true if a key exists in the settings file **or** in the matching
    environment variable (same merge as runtime). ``from_file`` / ``from_env``
    tell the UI where the effective credential comes from for messaging.
    """
    out = json.loads(json.dumps(data))
    keys = out.get("keys")
    if isinstance(keys, dict):
        masked: dict[str, Any] = {}
        for pname, val in keys.items():
            ps = str(pname)
            file_s = str(val).strip() if val is not None else ""
            env_s, env_hint = _env_secret_and_hint(ps)
            from_file = bool(file_s)
            from_env = bool(env_s)
            eff = merge_key(env_s, file_s)
            set_eff = bool(eff)
            if from_file:
                preview = _mask_key(file_s)
            elif from_env:
                preview = _mask_key(env_s)
            else:
                preview = ""
            entry: dict[str, Any] = {
                "set": set_eff,
                "from_file": from_file,
                "from_env": from_env,
                "preview": preview,
            }
            if from_env and env_hint:
                entry["env_hint"] = env_hint
            masked[pname] = entry
        out["keys"] = masked
    raw_b = ""
    if isinstance(out.get("openai_compatible_base_url"), str):
        raw_b = str(out["openai_compatible_base_url"]).strip()
    env_b = _env_trim("LENSES_OPENAI_COMPAT_BASE_URL").rstrip("/")
    eff_b = merged_openai_compat_base_url(out)
    from_file_b = bool(raw_b)
    from_env_b = bool(env_b)
    out["openai_compatible_endpoint"] = {
        "set": bool(eff_b),
        "from_file": from_file_b,
        "from_env": from_env_b and not from_file_b,
        "preview": (eff_b[:96] + "…") if len(eff_b) > 96 else eff_b,
        "env_hint": "LENSES_OPENAI_COMPAT_BASE_URL",
    }
    if "openai_compatible_base_url" in out:
        del out["openai_compatible_base_url"]
    return out


def merge_key(env_val: str, file_val: str) -> str:
    """Non-empty file key overrides env for local dev."""
    ft = (file_val or "").strip()
    if ft:
        return ft
    return (env_val or "").strip()


def merged_openai_compat_base_url(raw: dict[str, Any]) -> str:
    """HTTP(S) origin without ``/v1`` — file value overrides ``LENSES_OPENAI_COMPAT_BASE_URL``."""
    env_b = _env_trim("LENSES_OPENAI_COMPAT_BASE_URL").rstrip("/")
    file_b = ""
    if isinstance(raw.get("openai_compatible_base_url"), str):
        file_b = str(raw["openai_compatible_base_url"]).strip().rstrip("/")
    if file_b:
        return file_b
    return env_b


def merge_save(workspace_root: Path, incoming: dict[str, Any]) -> dict[str, Any]:
    """Merge POST payload into existing file; empty string for a key means keep previous."""
    cur = load_raw(workspace_root)
    for k, v in incoming.items():
        if k == "keys" and isinstance(v, dict) and isinstance(cur.get("keys"), dict):
            ck = dict(cur["keys"])
            for kk, vv in v.items():
                if not isinstance(vv, str):
                    continue
                if vv.strip() == "":
                    continue
                ck[str(kk)] = vv
            cur["keys"] = ck
        elif k == "main_models" and isinstance(v, dict):
            mm = dict(cur.get("main_models") or {})
            mm.update(v)
            cur["main_models"] = mm
        elif k == "pools" and isinstance(v, dict):
            pl = dict(cur.get("pools") or {})
            for pk, pv in v.items():
                if isinstance(pv, list):
                    pl[str(pk)] = pv
            cur["pools"] = pl
        elif k == "classifier_models" and isinstance(v, dict):
            cm = dict(cur.get("classifier_models") or {})
            for ck, cv in v.items():
                if isinstance(cv, str):
                    cm[str(ck)] = cv
            cur["classifier_models"] = cm
        elif k == "task_routes" and isinstance(v, dict):
            tr = dict(cur.get("task_routes") or {})
            for tk, tv in v.items():
                tks = str(tk).strip()
                if isinstance(tv, dict):
                    pr = str(tv.get("privacy") or "").strip().lower()
                    if pr not in ("local_only", "prefer_local", "cloud_allowed"):
                        pr = "cloud_allowed"
                    stack: list[str] = []
                    ms_in = tv.get("model_stack")
                    if isinstance(ms_in, list):
                        for x in ms_in:
                            s = str(x or "").strip()
                            if s:
                                stack.append(s)
                    model_single = str(tv.get("model", "") or "").strip()
                    if stack:
                        model_single = stack[0]
                    elif model_single:
                        stack = [model_single]
                    tr[tks] = {
                        "provider": str(tv.get("provider", "") or "").strip(),
                        "model": model_single,
                        "model_stack": stack,
                        "fallback_provider": str(tv.get("fallback_provider", "") or "").strip(),
                        "fallback_model": str(tv.get("fallback_model", "") or "").strip(),
                        "privacy": pr,
                    }
            cur["task_routes"] = tr
        elif k == "fallback_route" and isinstance(v, dict):
            cur["fallback_route"] = {
                "provider": str(v.get("provider", "") or "").strip(),
                "model": str(v.get("model", "") or "").strip(),
            }
        elif k == "openai_compatible_base_url" and isinstance(v, str):
            # Empty string from a partial client payload must not wipe a stored URL + break gateway auth.
            if v.strip():
                cur["openai_compatible_base_url"] = v.strip()
        elif k == "custom_provider" and isinstance(v, dict):
            base_cp = cur.get("custom_provider") if isinstance(cur.get("custom_provider"), dict) else {}
            d0 = _DEFAULT.get("custom_provider") if isinstance(_DEFAULT.get("custom_provider"), dict) else {}
            cp = {**d0, **base_cp}
            for ck, cv in v.items():
                cks = str(ck)
                if cks == "display_name" and isinstance(cv, str):
                    cp["display_name"] = cv.strip()[:120]
                elif cks == "transport" and isinstance(cv, str):
                    t = cv.strip()
                    if t in ("openai_compatible", "anthropic_messages", "custom_adapter"):
                        cp["transport"] = t
                elif cks == "auth" and isinstance(cv, str):
                    a = cv.strip()
                    if a in ("bearer", "none"):
                        cp["auth"] = a
            cur["custom_provider"] = cp
        elif k == "first_run_wizard_dismissed":
            cur["first_run_wizard_dismissed"] = bool(v)
        elif k not in (
            "keys",
            "main_models",
            "pools",
            "classifier_models",
            "task_routes",
            "fallback_route",
            "openai_compatible_base_url",
            "custom_provider",
        ):
            cur[k] = v
    _normalize_settings(cur)
    return cur
