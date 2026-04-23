"""Compile Cursor Launch Pack (markdown-first tree + manifest) for Blueprints Wizard (experimental)."""

from __future__ import annotations

import io
import json
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from lenses.blueprints_wizard.artifact_export_markdown import render_artifact_record_markdown
from lenses.blueprints_wizard.artifact_generation_normalize import normalize_artifact_generation
from lenses.blueprints_wizard.launch_pack_scope import CONTRACT_LIKE_KEYS, resolve_launch_pack_artifact_keys
from lenses.blueprints_wizard.prompt_materializer import NullPromptMaterializer, PromptMaterializer
from lenses.blueprints_wizard.wizard_domain_normalize import normalize_wizard_domain


LAUNCH_PACK_MANIFEST_VERSION = 1

_MAX_CAPSULE_CHARS = 12_000


class StrictApprovalError(Exception):
    """Raised when ``strict_approval`` is set and an expanded artifact is not approved or locked."""

    def __init__(self, keys: list[str]):
        self.keys = keys
        super().__init__("strict_approval_failed")


def _truthy_strict_approval(raw: Any) -> bool:
    if raw is True:
        return True
    if isinstance(raw, str):
        return raw.strip().lower() in ("1", "true", "yes", "on")
    return False


def build_launch_pack_zip_bytes(pack: CompiledLaunchPack) -> bytes:
    """Zip all pack files into a single archive (in-memory bytes)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel, text in pack.files:
            zf.writestr(rel, text.encode("utf-8"))
    return buf.getvalue()


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _approved_status(rec: Any) -> str:
    if not isinstance(rec, dict):
        return "missing"
    return str(rec.get("review_status") or "pending").strip().lower()


def _derive_allowed_write_scope(
    wd: dict[str, Any],
    build_pack: dict[str, Any],
) -> dict[str, Any]:
    mp = str(wd.get("mutation_policy") or "read_only_analysis")
    spec = wd.get("scope_spec")
    repo_paths: list[str] = []
    if isinstance(spec, dict):
        rp = spec.get("repo_paths")
        if isinstance(rp, list):
            repo_paths = [str(x).strip() for x in rp if str(x).strip()][:32]
    globs = list(build_pack.get("allowed_write_globs") or [])
    if isinstance(globs, list):
        globs = [str(g).strip() for g in globs if str(g).strip()][:64]
    else:
        globs = []
    return {
        "mutation_policy": mp,
        "repo_paths": repo_paths,
        "allowed_write_globs": globs,
    }


def _derive_guardrails(wd: dict[str, Any], build_pack: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    mp = str(wd.get("mutation_policy") or "")
    if mp:
        lines.append(f"Mutation policy: {mp}")
    al = str(wd.get("autonomy_level") or "")
    if al:
        lines.append(f"Autonomy level: {al}")
    gn = str(build_pack.get("guardrail_notes") or "").strip()
    if gn:
        lines.append(gn)
    return lines[:32]


@dataclass
class CompiledLaunchPack:
    manifest: dict[str, Any]
    files: list[tuple[str, str]] = field(default_factory=list)  # relative_path, utf-8 text


def compile_cursor_launch_pack(
    session_id: str,
    payload: dict[str, Any],
    body: dict[str, Any],
    materializer: PromptMaterializer | None = None,
) -> tuple[CompiledLaunchPack, list[str]]:
    """
    Build manifest + file list for preview or export.

    ``body`` may include ``artifact_keys`` (required), ``closure_options`` (optional override of scope_spec).
    """
    warnings: list[str] = []
    wd_raw = payload.get("wizard_domain")
    if not isinstance(wd_raw, dict):
        wd_raw = {}
    wd = normalize_wizard_domain(wd_raw)

    ag = normalize_artifact_generation(wd.get("artifact_generation"))
    arts = ag.get("artifacts")
    if not isinstance(arts, dict):
        arts = {}

    raw_keys = body.get("artifact_keys")
    if not isinstance(raw_keys, list) or len(raw_keys) == 0:
        raise ValueError("invalid_artifact_keys")

    base_keys: list[str] = []
    for x in raw_keys:
        k = str(x).strip()
        if k:
            base_keys.append(k)
    if not base_keys:
        raise ValueError("invalid_artifact_keys")

    closure_override = body.get("closure_options")
    if isinstance(closure_override, list) and len(closure_override) > 0:
        closure_opts = [str(x).strip() for x in closure_override if str(x).strip()]
    else:
        spec = wd.get("scope_spec")
        closure_opts = list((spec or {}).get("closure_options") or []) if isinstance(spec, dict) else []

    expanded, trace = resolve_launch_pack_artifact_keys(base_keys, closure_opts, arts)
    if not expanded:
        raise ValueError("invalid_artifact_keys")

    if _truthy_strict_approval(body.get("strict_approval")):
        bad = [
            ak
            for ak in expanded
            if _approved_status(arts.get(ak)) not in ("approved", "locked")
        ]
        if bad:
            raise StrictApprovalError(sorted(set(bad)))

    for ak in expanded:
        rec = arts.get(ak)
        st = _approved_status(rec)
        if st not in ("approved", "locked") and st != "missing":
            warnings.append(f"artifact `{ak}` review_status is `{st}` (not approved)")

    mat = materializer or NullPromptMaterializer()
    build_pack = wd.get("build_pack_plan")
    if not isinstance(build_pack, dict):
        build_pack = {}
    pr = wd.get("prompt_recipe")
    if not isinstance(pr, dict):
        pr = {}

    approval_counts: dict[str, int] = {"approved_or_locked": 0, "draft_or_other": 0, "missing": 0}
    for ak in expanded:
        rec = arts.get(ak)
        if not isinstance(rec, dict):
            approval_counts["missing"] += 1
            continue
        st = _approved_status(rec)
        if st in ("approved", "locked"):
            approval_counts["approved_or_locked"] += 1
        else:
            approval_counts["draft_or_other"] += 1

    manifest: dict[str, Any] = {
        "schema_version": LAUNCH_PACK_MANIFEST_VERSION,
        "kind": "cursor_launch_pack",
        "created_at": _utc_now(),
        "session_id": session_id,
        "session_title": str(payload.get("title") or "")[:500],
        "base_artifact_keys": base_keys,
        "closure_options_applied": closure_opts,
        "closure_trace": trace,
        "expanded_artifact_keys": expanded,
        "allowed_write_scope": _derive_allowed_write_scope(wd, build_pack),
        "guardrails": _derive_guardrails(wd, build_pack),
        "prompt_recipe": {
            "recipe_id": pr.get("recipe_id", ""),
            "intent": pr.get("intent", "clarify"),
            "prompt_mode": pr.get("prompt_mode", "static"),
            "template_ref": pr.get("template_ref", ""),
            "placeholder_summary": pr.get("placeholder_summary", ""),
            "materialization_inputs": list(pr.get("materialization_inputs") or []),
        },
        "approval_summary": approval_counts,
    }

    files: list[tuple[str, str]] = []

    files.append(("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"))

    index_md = "\n".join(
        [
            "# Cursor Launch Pack",
            "",
            "Open this folder as a workspace in Cursor (or copy into a repo).",
            "",
            "- Read `RUNBOOK.md` for execution steps.",
            "- `scope/SCOPE.md` describes the selected scope and closure.",
            "- `nodes/` holds artifact slices included in this export.",
            "- `recipes/` holds prompt recipes and placeholders.",
            "- `runs/` and `history/` are reserved for future run logs.",
            "",
        ]
    )
    files.append(("INDEX.md", index_md))

    rp = wd.get("run_plan")
    run_lines = ["# Runbook", ""]
    if isinstance(rp, dict):
        run_lines.append(f"## {rp.get('title') or 'Run plan'}")
        run_lines.append("")
        steps = rp.get("steps")
        if isinstance(steps, list):
            for i, s in enumerate(steps, start=1):
                if not isinstance(s, dict):
                    continue
                t = str(s.get("title") or "").strip() or "(step)"
                d = str(s.get("detail") or "").strip()
                run_lines.append(f"{i}. **{t}**")
                if d:
                    run_lines.append(f"   {d}")
                run_lines.append("")
        run_lines.append("## Scope note")
        run_lines.append(
            "Steps above are the full session run plan; export scope is limited to the artifact keys "
            "listed in `manifest.json` under `expanded_artifact_keys`."
        )
        run_lines.append("")
    else:
        run_lines.append("_(no run plan in session)_")
        run_lines.append("")
    files.append(("RUNBOOK.md", "\n".join(run_lines)))

    spec = wd.get("scope_spec")
    scope_lines = ["# Scope", ""]
    if isinstance(spec, dict):
        scope_lines.append(f"**Summary:** {spec.get('summary') or '—'}")
        scope_lines.append("")
        scope_lines.append(f"**Constraints:** {spec.get('constraints_note') or '—'}")
        scope_lines.append("")
        scope_lines.append("**Closure trace:**")
        for line in trace:
            scope_lines.append(f"- {line}")
        scope_lines.append("")
    files.append(("scope/SCOPE.md", "\n".join(scope_lines)))

    fb = wd.get("foundation_brief")
    cap_md = ["# Foundation context (capsule)", ""]
    if isinstance(fb, dict):
        md = str(fb.get("markdown") or "")
        if len(md) > _MAX_CAPSULE_CHARS:
            md = md[:_MAX_CAPSULE_CHARS] + "\n\n… _(truncated)_\n"
        cap_md.append(md if md else "_(empty)_")
    else:
        cap_md.append("_(empty)_")
    cap_md.append("")
    files.append(("context/capsules/foundation_brief.md", "\n".join(cap_md)))

    ledger = wd.get("assumption_ledger")
    led_lines = ["# Assumptions (capsule)", ""]
    if isinstance(ledger, list):
        for row in ledger[:24]:
            if not isinstance(row, dict):
                continue
            txt = str(row.get("text") or "").strip()
            if txt:
                led_lines.append(f"- {txt}")
        led_lines.append("")
    else:
        led_lines.append("_(none)_")
        led_lines.append("")
    files.append(("context/capsules/assumptions.md", "\n".join(led_lines)))

    for ak in expanded:
        rec = arts.get(ak)
        if not isinstance(rec, dict):
            body_md = render_artifact_record_markdown(ak, {})
        else:
            body_md = render_artifact_record_markdown(ak, rec)
        files.append((f"nodes/{ak}.md", body_md))

    for ak in sorted(CONTRACT_LIKE_KEYS & set(expanded)):
        files.append(
            (
                f"contracts/{ak}.md",
                "\n".join(
                    [
                        f"# {ak} (contract surface)",
                        "",
                        f"Canonical export: [nodes/{ak}.md](../nodes/{ak}.md).",
                        "",
                    ]
                ),
            )
        )

    recipe_body = ""
    mode = str(pr.get("prompt_mode") or "static")
    if mode == "build_time_dynamic":
        recipe_body = mat.materialize_placeholder(pr)
    elif mode == "runtime_dynamic":
        recipe_body = "\n".join(
            [
                "# Runtime dynamic prompt",
                "",
                "This recipe is intended to be resolved at runtime in Cursor (e.g. via Rules or Agent).",
                "",
                str(pr.get("placeholder_summary") or "").strip() or "_(no summary)_",
                "",
            ]
        )
    else:
        recipe_body = "\n".join(
            [
                "# Static prompt recipe",
                "",
                f"Template ref: `{pr.get('template_ref') or '—'}`",
                "",
                "Variables:",
                "",
            ]
        )
        vars_d = pr.get("variables")
        if isinstance(vars_d, dict):
            for k, v in list(vars_d.items())[:48]:
                recipe_body += f"- `{k}`: {v}\n"

    front = {
        "recipe_id": pr.get("recipe_id", ""),
        "intent": pr.get("intent", "clarify"),
        "prompt_mode": mode,
        "template_ref": pr.get("template_ref", ""),
    }
    recipes_md = "---\n" + json.dumps(front, ensure_ascii=False) + "\n---\n\n" + recipe_body
    files.append(("recipes/wizard_prompt.md", recipes_md))

    files.append(("runs/.gitkeep", "# Reserved for run logs\n"))
    files.append(("history/.gitkeep", "# Reserved for history\n"))

    return CompiledLaunchPack(manifest=manifest, files=files), warnings


def preview_pack(
    session_id: str,
    payload: dict[str, Any],
    body: dict[str, Any],
) -> dict[str, Any]:
    """JSON-serializable preview: manifest + file list with sizes."""
    pack, warnings = compile_cursor_launch_pack(session_id, payload, body)
    files_out: list[dict[str, Any]] = []
    for path, text in pack.files:
        b = text.encode("utf-8")
        files_out.append(
            {
                "path": path,
                "kind": "file",
                "size": len(b),
            }
        )
    return {
        "ok": True,
        "manifest": pack.manifest,
        "files": files_out,
        "warnings": warnings,
    }
