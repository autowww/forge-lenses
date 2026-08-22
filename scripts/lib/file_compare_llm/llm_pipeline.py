"""
Multi-pass LLM pipeline: understand each file, compare, then score.
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
from typing import Any

from .llm_openai_compat import chat_completion
from .normalize import FileProfile
from .template_render import load_system_prompt, render_template


def _strip_fence(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", t)
        if t.endswith("```"):
            t = t[: t.rfind("```")].rstrip()
    return t.strip()


def _first_json_object(text: str) -> str | None:
    """Best-effort: slice from first `{` through matching `}` for chatty models."""
    s = text
    start = s.find("{")
    if start < 0:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(s)):
        ch = s[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return s[start : i + 1]
    return None


def parse_llm_json(text: str) -> dict[str, Any]:
    stripped = _strip_fence(text)
    candidates = [stripped]
    inner = _first_json_object(stripped)
    if inner and inner != stripped:
        candidates.append(inner)
    for c in candidates:
        if not c.strip():
            continue
        try:
            out = json.loads(c, strict=False)
            if isinstance(out, dict):
                return out
        except json.JSONDecodeError:
            continue
    raise ValueError("Model response was not a JSON object")


def _json(obj: Any, cap: int | None = None) -> str:
    """Serialize to JSON. If cap is None or <= 0, never truncate."""
    s = json.dumps(obj, indent=2, ensure_ascii=False)
    if cap is None or cap <= 0:
        return s
    if len(s) > cap:
        return s[: cap // 2] + "\n…\n" + s[-cap // 2 :]
    return s


def _excerpt(fp: FileProfile, max_chars: int) -> str:
    """Full raw_text when max_chars is None or <= 0."""
    t = fp.raw_text
    if max_chars is None or max_chars <= 0 or len(t) <= max_chars:
        return t
    half = max_chars // 2 - 20
    return t[:half] + "\n… [middle omitted] …\n" + t[-half:]


def _evidence_slice(evidence: dict[str, Any], label: str, cap: int | None) -> str:
    key = "file_a" if label == "A" else "file_b"
    blk = evidence.get(key) or {}
    pair = evidence.get("pairwise") or {}
    slim = {key: blk, "pairwise": pair}
    return _json(slim, cap)


def _llm_eta_suffix(completed_durations: list[float]) -> str:
    n = len(completed_durations)
    if n == 0 or n >= 4:
        return ""
    rem = 4 - n
    avg = sum(completed_durations) / n
    return f" | LLM est. ~{rem * avg:.0f}s left ({rem} call(s))"


def dimensions_table_md(profile: dict[str, Any]) -> str:
    lines: list[str] = []
    for d in profile.get("dimensions") or []:
        if not isinstance(d, dict):
            continue
        did = d.get("id", "")
        lab = d.get("label", "")
        why = d.get("why", "")
        lines.append(f"- **{lab}** (`{did}`): {why}")
    return "\n".join(lines) if lines else "(no dimension config)"


def run_llm_pipeline(
    *,
    profile: dict[str, Any],
    evidence: dict[str, Any],
    fa: FileProfile,
    fb: FileProfile,
    model: str | None,
    temperature: float,
    excerpt_cap: int,
    debug: bool,
    progress_log: Callable[[str], None] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Returns (merged_result, debug_dict)."""
    system = load_system_prompt()
    excerpts_cfg = profile.get("excerpts") or {}
    cap = int(excerpts_cfg.get("max_chars_per_file", excerpt_cap))

    ex_a = _excerpt(fa, cap)
    ex_b = _excerpt(fb, cap)
    # Evidence and prior-pass JSON are always serialized in full (no truncation).
    ev_full = _json(evidence, None)

    raw_log: dict[str, Any] = {}
    llm_durations: list[float] = []

    def log(msg: str) -> None:
        if progress_log:
            progress_log(msg)

    def call(user_content: str, tag: str) -> dict[str, Any]:
        log(f"LLM {tag}: sending request (user message {len(user_content):,} chars)…")
        t0 = time.monotonic()
        messages: list[dict[str, str]] = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ]
        res = chat_completion(messages=messages, model=model, temperature=temperature)
        if not res.ok:
            raise RuntimeError(f"LLM {tag} failed: {res.text}")
        if debug:
            raw_log[tag] = res.text
        try:
            out = parse_llm_json(res.text)
        except ValueError:
            repair = (
                "Your previous assistant message was not a single valid JSON object. "
                "Reply with ONLY one JSON object (no markdown fences, no commentary) "
                "that satisfies the same schema the user asked for."
            )
            messages = messages + [{"role": "assistant", "content": res.text}, {"role": "user", "content": repair}]
            res2 = chat_completion(messages=messages, model=model, temperature=0.0)
            if not res2.ok:
                raise RuntimeError(f"LLM {tag} JSON repair failed: {res2.text}") from None
            if debug:
                raw_log[f"{tag}_repair"] = res2.text
            out = parse_llm_json(res2.text)
        dt = time.monotonic() - t0
        llm_durations.append(dt)
        log(f"LLM {tag}: done in {dt:.1f}s ({len(res.text):,} chars response){_llm_eta_suffix(llm_durations)}")
        return out

    if cap <= 0:
        log("LLM context: full file text and full evidence JSON (no truncation).")
    else:
        log(f"LLM context: excerpts capped at {cap:,} chars per file; evidence JSON may be truncated.")

    p1a = call(
        render_template(
            "pass1_understand.md",
            {
                "__FILE_LABEL__": "A",
                "__EVIDENCE_SLICE_JSON__": _evidence_slice(evidence, "A", None),
                "__FILE_EXCERPT__": ex_a,
            },
        ),
        "pass1a",
    )
    p1b = call(
        render_template(
            "pass1_understand.md",
            {
                "__FILE_LABEL__": "B",
                "__EVIDENCE_SLICE_JSON__": _evidence_slice(evidence, "B", None),
                "__FILE_EXCERPT__": ex_b,
            },
        ),
        "pass1b",
    )
    p2 = call(
        render_template(
            "pass2_compare.md",
            {
                "__PASS1A_JSON__": _json(p1a, None),
                "__PASS1B_JSON__": _json(p1b, None),
                "__EVIDENCE_FULL_JSON__": ev_full,
                "__EXCERPT_A__": ex_a,
                "__EXCERPT_B__": ex_b,
            },
        ),
        "pass2",
    )
    p3 = call(
        render_template(
            "pass3_score.md",
            {
                "__PASS2_JSON__": _json(p2, None),
                "__EVIDENCE_FULL_JSON__": ev_full,
                "__DIMENSIONS_TABLE_MD__": dimensions_table_md(profile),
            },
        ),
        "pass3",
    )

    merged = {
        "pass1_file_a": p1a,
        "pass1_file_b": p1b,
        "pass2": p2,
        "pass3": p3,
        "evidence": evidence,
        "file_profiles": {"a": fa.to_dict(), "b": fb.to_dict()},
    }
    dbg = {"raw_responses": raw_log} if debug else {}
    return merged, dbg
