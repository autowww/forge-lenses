#!/usr/bin/env python3
"""
Hybrid file comparison: normalization → deterministic evidence → multi-pass LLM.

Environment (same as Situ8 taxonomy drafting):
  LLM_BASE_URL, LLM_MODEL, LLM_API_KEY, LLM_NGROK_BYPASS

Default outputs in --out-dir:
  comparison_report.md, comparison_report.json, optional comparison_debug.json

Progress messages go to stderr unless --quiet.

Examples:
  python3 scripts/compare_files_llm_report.py --a path/A.json --b path/B.json --out-dir .
  python3 scripts/compare_files_llm_report.py --a A.json --b B.md --out reports/summary.md --env-file env.local
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from lib.file_compare_llm.deterministic import (  # noqa: E402
    collect_signals,
    diff_stats,
    infer_compare_mode,
    lines_of,
    normalize_newlines,
    read_text,
)
from lib.file_compare_llm.evidence import build_evidence  # noqa: E402
from lib.file_compare_llm.llm_pipeline import run_llm_pipeline  # noqa: E402
from lib.file_compare_llm.normalize import load_profile, normalize_file  # noqa: E402
from lib.file_compare_llm.report_hybrid import render_comparison_report  # noqa: E402


def load_env_file(path: Path) -> None:
    import os

    raw = path.read_text(encoding="utf-8")
    for line in raw.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("export "):
            s = s[7:].lstrip()
        if "=" not in s:
            continue
        key, _, val = s.partition("=")
        key = key.strip()
        if not key or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key):
            continue
        val = val.strip()
        if (val.startswith("'") and val.endswith("'")) or (val.startswith('"') and val.endswith('"')):
            val = val[1:-1]
        os.environ[key] = val


def _resolve_output_paths(
    *,
    out: Path | None,
    out_dir: Path,
    basename: str,
) -> tuple[Path, Path, Path]:
    if out is not None:
        md = out.expanduser().resolve()
        stem = md.with_suffix("")
        return md, Path(str(stem) + ".json"), Path(str(stem) + "_debug.json")
    d = out_dir.expanduser().resolve()
    d.mkdir(parents=True, exist_ok=True)
    base = basename.strip() or "comparison_report"
    return d / f"{base}.md", d / f"{base}.json", d / f"{base}_debug.json"


class Progress:
    """Human-readable stderr progress with elapsed time."""

    def __init__(self, *, quiet: bool) -> None:
        self.quiet = quiet
        self.t0 = time.monotonic()

    def log(self, msg: str) -> None:
        if self.quiet:
            return
        elapsed = time.monotonic() - self.t0
        print(f"[compare {elapsed:8.1f}s] {msg}", file=sys.stderr, flush=True)

    def bar(self, step: int, total: int, width: int = 22) -> str:
        if total <= 0:
            return "[" + "-" * width + "]"
        fill = min(width, max(0, int(width * step / total)))
        return "[" + ("#" * fill) + ("-" * (width - fill)) + "]"


def main() -> int:
    p = argparse.ArgumentParser(description="Hybrid compare two files (evidence + multi-pass LLM).")
    p.add_argument("--a", required=True, type=Path, help="Path to first file")
    p.add_argument("--b", required=True, type=Path, help="Path to second file")
    p.add_argument("--out", type=Path, default=None, help="Output Markdown path (sets sibling .json / _debug.json)")
    p.add_argument("--out-dir", type=Path, default=Path("."), help="Directory for comparison_report.* (default .)")
    p.add_argument("--basename", type=str, default="comparison_report", help="Base name without extension")
    p.add_argument("--config", type=Path, default=None, help="YAML profile (default: packaged compare_profile.yaml)")
    p.add_argument("--json-out", type=Path, default=None, help="Override JSON output path")
    p.add_argument("--debug-json", action="store_true", help="Write debug JSON with raw LLM responses")
    p.add_argument("--mode", choices=("auto", "document", "code"), default="auto")
    p.add_argument("--deterministic-only", action="store_true", help="Skip LLM; evidence + stub report only")
    p.add_argument("--normalize-lines", action="store_true", help="Normalize CRLF before read")
    p.add_argument(
        "--max-prompt-chars-per-file",
        type=int,
        default=0,
        help="Max UTF-8 chars per file in LLM prompts; 0 = full file (default). >0 omits middle with a marker.",
    )
    p.add_argument("--temperature", type=float, default=0.2)
    p.add_argument("--model", type=str, default=None)
    p.add_argument("--env-file", type=Path, default=None)
    p.add_argument(
        "--technical-markdown",
        action="store_true",
        help="Append extra deterministic rubric JSON (legacy signals) to the Markdown appendix.",
    )
    p.add_argument("--quiet", action="store_true", help="Suppress stderr progress messages")
    args = p.parse_args()

    prog = Progress(quiet=args.quiet)
    total_steps = 6 if not args.deterministic_only else 5
    step = 0

    def bump(msg: str) -> None:
        nonlocal step
        step += 1
        prog.log(f"{prog.bar(step, total_steps)} {msg}")

    if args.env_file is not None:
        ef = args.env_file.expanduser().resolve()
        if not ef.is_file():
            print(f"Env file not found: {ef}", file=sys.stderr)
            return 2
        load_env_file(ef)

    path_a = args.a.expanduser().resolve()
    path_b = args.b.expanduser().resolve()
    if not path_a.is_file() or not path_b.is_file():
        print("Both --a and --b must be existing files.", file=sys.stderr)
        return 2

    prog.log(f"Files: {path_a.name} ({path_a.stat().st_size:,} bytes) vs {path_b.name} ({path_b.stat().st_size:,} bytes)")

    bump("Load YAML profile")
    profile = load_profile(args.config.expanduser().resolve() if args.config else None)

    excerpt_cfg = profile.get("excerpts") or {}
    try:
        excerpt_cap = int(excerpt_cfg.get("max_chars_per_file", args.max_prompt_chars_per_file))
    except (TypeError, ValueError):
        excerpt_cap = int(args.max_prompt_chars_per_file)
    if excerpt_cap <= 0:
        prog.log("Excerpt policy: full file text in every LLM prompt (no middle truncation).")
    else:
        prog.log(f"Excerpt policy: each file truncated to ~{excerpt_cap:,} chars for LLM prompts (CLI/profile cap).")

    bump(f"Normalize file A — {path_a.name}")
    fa = normalize_file(path_a, profile)
    prog.log(
        f"  type={fa.file_type}, parse_ok={fa.parse_ok}, records={len(fa.structured_records or [])}, "
        f"raw_chars={len(fa.raw_text):,}, entities={len(fa.entity_candidates)}"
    )

    bump(f"Normalize file B — {path_b.name}")
    fb = normalize_file(path_b, profile)
    prog.log(
        f"  type={fb.file_type}, parse_ok={fb.parse_ok}, records={len(fb.structured_records or [])}, "
        f"raw_chars={len(fb.raw_text):,}, entities={len(fb.entity_candidates)}"
    )

    if args.normalize_lines:
        fa.raw_text = normalize_newlines(fa.raw_text)
        fb.raw_text = normalize_newlines(fb.raw_text)

    bump("Build deterministic evidence pack")
    evidence = build_evidence(profile, fa, fb)
    pair = evidence.get("pairwise") or {}
    prog.log(
        f"  Jaccard(entity ids)={pair.get('jaccard_entity_ids')}, line_similarity={pair.get('similarity_ratio_lines')}, "
        f"ids only in A={len(pair.get('entity_ids_only_in_a') or [])}, only in B={len(pair.get('entity_ids_only_in_b') or [])}"
    )

    merged: dict = {
        "evidence": evidence,
        "file_profiles": {"a": fa.to_dict(), "b": fb.to_dict()},
        "pass1_file_a": None,
        "pass1_file_b": None,
        "pass2": None,
        "pass3": None,
    }
    debug: dict = {}

    if not args.deterministic_only:
        import os

        if not os.environ.get("LLM_BASE_URL", "").strip():
            print("Missing LLM_BASE_URL (or use --deterministic-only)", file=sys.stderr)
            return 2
        bump("Run LLM pipeline (4 chat calls: pass1a, pass1b, pass2, pass3)")
        try:
            merged_llm, debug = run_llm_pipeline(
                profile=profile,
                evidence=evidence,
                fa=fa,
                fb=fb,
                model=args.model,
                temperature=args.temperature,
                excerpt_cap=excerpt_cap,
                debug=args.debug_json,
                progress_log=None if args.quiet else prog.log,
            )
            merged.update(merged_llm)
        except Exception as e:  # noqa: BLE001
            print(f"LLM pipeline failed: {e}", file=sys.stderr)
            merged["pipeline_error"] = str(e)

    bump("Render Markdown + write JSON")
    md_path, json_path, debug_path = _resolve_output_paths(
        out=args.out,
        out_dir=args.out_dir,
        basename=args.basename,
    )
    if args.json_out is not None:
        json_path = args.json_out.expanduser().resolve()

    technical_extra: dict | None = None
    if args.technical_markdown:
        mode = infer_compare_mode(path_a, path_b, args.mode)
        ta, ra, sha = read_text(path_a)
        tb, rb, shb = read_text(path_b)
        if args.normalize_lines:
            ta = normalize_newlines(ta)
            tb = normalize_newlines(tb)
        dst = diff_stats(lines_of(ta), lines_of(tb))
        sig_a = collect_signals(path_a, ta, mode, raw_byte_size=ra, sha256_hex=sha)
        sig_b = collect_signals(path_b, tb, mode, raw_byte_size=rb, sha256_hex=shb)
        technical_extra = {
            "legacy_compare_mode": mode,
            "legacy_signals_a": sig_a.__dict__,
            "legacy_signals_b": sig_b.__dict__,
            "legacy_diff_similarity": dst.similarity_ratio,
        }

    md = render_comparison_report(
        merged=merged,
        name_a=path_a.name,
        name_b=path_b.name,
        technical_extra=technical_extra,
    )
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(md, encoding="utf-8")

    json_payload = {**merged, "debug": debug if args.debug_json else None}
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(json_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    if args.debug_json and debug:
        debug_path.parent.mkdir(parents=True, exist_ok=True)
        debug_path.write_text(json.dumps(debug, indent=2, ensure_ascii=False), encoding="utf-8")
        prog.log(f"Wrote debug JSON: {debug_path}")

    prog.log(f"Wrote Markdown: {md_path}")
    prog.log(f"Wrote JSON:     {json_path}")
    prog.log(f"Finished in {time.monotonic() - prog.t0:.1f}s total.")
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
