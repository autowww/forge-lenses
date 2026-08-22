# File compare + LLM report (forge-lenses)

Standalone script: [`scripts/compare_files_llm_report.py`](../scripts/compare_files_llm_report.py).

## Purpose

Compare two UTF-8 files through a **hybrid pipeline**:

1. **Normalization** — typed `FileProfile` per side (JSON/YAML/Markdown/text/code-ish), optional wrapper flattening and key aliasing from YAML profile (`scripts/lib/file_compare_llm/compare_profile.yaml`).
2. **Deterministic evidence** — duplicate IDs, broken refs, drift flags, overlap/diff candidates, line stats (clues only; no automatic “winner”).
3. **Optional multi-pass LLM** — OpenAI-compatible chat using the **same environment variables as Situ8 taxonomy drafting** (not the Lenses Studio `LENSES_OPENAI_COMPAT_*` stack): pass 1×2 (per file), pass 2 (compare), pass 3 (scorecard + executive summary).

Design note: [`docs/design/file-compare-hybrid-pipeline.md`](../design/file-compare-hybrid-pipeline.md).

## Environment (Situ8-aligned)

Set before running (or `source` a **gitignored** env file such as `Situ8/taxonomy-llm.local.env`), or pass **`--env-file`** to the script (e.g. workspace [`file-compare-reports/llm-instance.local.env`](../../../file-compare-reports/llm-instance.local.env) — gitignored; copy from [`llm-instance.env.example`](../../../file-compare-reports/llm-instance.env.example)):

| Variable | Required | Notes |
|----------|----------|--------|
| `LLM_BASE_URL` | Yes (unless `--deterministic-only`) | OpenAI-compatible base including `/v1`, no trailing slash |
| `LLM_MODEL` | No | Model id on your server |
| `LLM_API_KEY` | No | Bearer token if required |
| `LLM_NGROK_BYPASS` | No | `1` if you get HTML instead of JSON behind ngrok free |

Reference implementation in Situ8: `Situ8/scripts/taxonomy_llm_openai.py`.

## CLI examples

From **forge-lenses** repo root (default bundle `comparison_report.md` + `comparison_report.json` in `--out-dir`):

```bash
python3 scripts/compare_files_llm_report.py \
  --a /path/to/A.json \
  --b /path/to/B.json \
  --out-dir /path/to/reports
```

Same paths with explicit basename:

```bash
python3 scripts/compare_files_llm_report.py --a A.json --b B.json \
  --out-dir . --basename my_compare
# → ./my_compare.md, ./my_compare.json
```

Backward-compatible single `--out` path (siblings: stem `.json`, stem `_debug.json`):

```bash
python3 scripts/compare_files_llm_report.py --a A.json --b B.json --out /path/to/report.md
```

Optional **`--config PATH`** overrides the packaged profile. **`--debug-json`** writes `*_debug.json` with raw model responses when the LLM path succeeds.

Deterministic only (no network):

```bash
python3 scripts/compare_files_llm_report.py --deterministic-only \
  --a path/A.md --b path/B.md --out report.md --json-out report.json
```

Compare two **Situ8 taxonomy LLM artifact** JSON runs (output under gitignored `taxonomy-llm-artifacts/`):

```bash
python3 scripts/compare_files_llm_report.py --deterministic-only \
  --a ../Situ8/taxonomy-llm-artifacts/taxonomy-logic-run-20260414T084528Z.json \
  --b ../Situ8/taxonomy-llm-artifacts/taxonomy-logic-run-20260414T173858Z.json \
  --out ../Situ8/taxonomy-llm-artifacts/compare-run.md \
  --json-out ../Situ8/taxonomy-llm-artifacts/compare-run.json
```

With LLM narrative, after exporting `LLM_BASE_URL`, or using `--env-file`:

```bash
python3 scripts/compare_files_llm_report.py \
  --env-file ../file-compare-reports/llm-instance.local.env \
  --a ../Situ8/taxonomy-llm-artifacts/run-a.json \
  --b ../Situ8/taxonomy-llm-artifacts/run-b.json \
  --out ../Situ8/taxonomy-llm-artifacts/compare-run.md
```

## Modes (`--technical-markdown` only)

- `--mode auto` (default): both files use a known code extension → **code** legacy rubric signals; otherwise **document** (includes `.json`).
- `--mode document` / `--mode code`: force legacy signal collection for the optional technical appendix.

## Markdown style

- Default report is **human-first**: executive summary, scorecard, common themes, material differences, entity deltas, bottom line, then **appendix: deterministic evidence** (JSON) plus normalization warnings when present.
- **`--technical-markdown`** appends an extra JSON block with legacy `collect_signals` / `diff_stats` payloads for debugging.
- **`comparison_report.json`** (or `--json-out`) holds merged profiles, evidence, pass outputs, and optional `pipeline_error` / `debug`.

## Limitations

- By default the **entire file** is sent in LLM prompts (`--max-prompt-chars-per-file` default **0** = no limit; profile `excerpts.max_chars_per_file` can set a positive cap). Very large files may exceed the model’s context window.
- Progress and ETA hints print to **stderr**; use **`--quiet`** to suppress them.
- Multi-pass LLM is **four** chat calls per compare (latency/cost).
- Code mode legacy signals use **heuristics**, not AST.
- LLM output is advisory; verify against sources.

## Secrets

Do not commit real URLs, keys, or chat transcripts. Keep local env files gitignored (see `Situ8/.gitignore` patterns for taxonomy LLM).
