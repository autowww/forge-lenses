# Hybrid file comparison pipeline (forge-lenses)

This note describes the **normalization → deterministic evidence → multi-pass LLM** pipeline behind `scripts/compare_files_llm_report.py` and `scripts/lib/file_compare_llm/`.

## Layers

| Layer | Module | Role |
| --- | --- | --- |
| Normalization | `normalize.py` | Per path: detect type (JSON, YAML, Markdown, plain text, code-ish), parse when possible, optional wrapper flattening and key aliasing from YAML profile, `section_candidates` / `entity_candidates`, warnings. Output: `FileProfile` (serialized in JSON as `file_profiles`). |
| Evidence | `evidence.py` | Pairwise and per-file **clues**: counts, duplicate IDs, malformed ID pattern hits, broken cross-refs, lexical drift flags, overlap/diff candidates, line stats. Output: `EvidencePack` (JSON object under `evidence`). No semantic “winner”. |
| LLM | `llm_pipeline.py` + `prompt_templates/*.md` | Four chat calls: pass 1 for file A, pass 1 for file B, pass 2 alignment/compare, pass 3 scorecard + executive bullets. Templates are loaded from disk; profile YAML supplies dimension text for pass 3. |
| Report | `report_hybrid.py` | Human-first Markdown: executive summary, scorecard, common ground, material differences (subsections), entity table, bottom line, appendix with deterministic evidence and optional normalization warnings. |

## Data contracts (JSON)

- **`file_profiles.a` / `file_profiles.b`** — dict form of `FileProfile` (`path`, `file_type`, `raw_text`, `structured_records`, `normalization_warnings`, …).
- **`evidence`** — nested `file_a`, `file_b`, `pairwise` as built by `evidence.py`.
- **`pass1_file_a`**, **`pass1_file_b`** — model JSON: purpose, audience, themes, strengths/weaknesses, etc. (see `pass1_understand.md`).
- **`pass2`** — model JSON: `common_themes`, `material_differences` (map of subsection keys), aligned pairs, `missing_in_a` / `missing_in_b`, etc. (see `pass2_compare.md`).
- **`pass3`** — model JSON: `executive_summary_bullets`, `scorecard` rows (`dimension_id`, `file_a`, `file_b`, `winner`, `why_it_matters`), `what_is_common`, `entity_deltas`, `human_bottom_line`, optional `appendix_notes` (see `pass3_score.md`).

The CLI writes **`comparison_report.json`** (default) merging the above plus optional `debug` and `pipeline_error` on failure.

## Scoring philosophy

Deterministic metrics are **inputs and guardrails**, not a substitute for judgment. The model is instructed that evidence items are **clues**; pass 3 assigns numeric scores and narrative. If the LLM stack is unavailable, use **`--deterministic-only`** to emit evidence and a stub narrative block.

## Configuration and prompts

| Artifact | Path |
| --- | --- |
| Default profile | `scripts/lib/file_compare_llm/compare_profile.yaml` |
| Override | `--config /path/to/profile.yaml` |
| Prompt templates | `scripts/lib/file_compare_llm/prompt_templates/` (`system.md`, `pass1_understand.md`, `pass2_compare.md`, `pass3_score.md`) |

Profile sections include `dimensions`, `excerpts`, `normalization` (wrapper flatten, key aliases, required fields), and `evidence` (entity id fields, reference checks, malformed ID regexes, lexical drift lists).

## CLI outputs

| Flag | Effect |
| --- | --- |
| `--out-dir DIR` | Write `comparison_report.md` and `.json` under `DIR` (default: current directory). |
| `--basename NAME` | Base filename without extension (default `comparison_report`). |
| `--out PATH.md` | Markdown path; siblings `PATH.json` and `PATH_debug.json` stem from the path without `.md`. |
| `--json-out` | Override JSON path only. |
| `--debug-json` | Include raw model text in `*_debug.json` and verbose `debug` in JSON when successful. |
| `--deterministic-only` | Skip LLM; evidence + stub sections. |
| `--technical-markdown` | Append legacy deterministic rubric payload (`collect_signals` / `diff_stats`) as an extra appendix JSON block. |
| `--max-prompt-chars-per-file N` | `0` (default): send **entire** UTF-8 file text in LLM prompts. `N>0` truncates the middle of each file only. |
| `--quiet` | Suppress stderr progress / ETA lines. |

**Context policy:** Evidence JSON and prior-pass JSON embedded in prompts are **not** truncated. The Markdown appendix dumps the full evidence JSON. Progress messages (including rough LLM ETA after each completed call) go to **stderr**.

## Reliability

`llm_pipeline.parse_llm_json` strips fences, attempts to slice the first top-level JSON object, and on parse failure performs **one** follow-up completion at temperature `0` asking for valid JSON only.

## Extension points

Add a new **profile** YAML (or fork `compare_profile.yaml`) with:

- `normalization.wrapper_flatten` / `key_aliases` / `required_fields` for another JSON schema.
- `evidence` rules for ID fields, reference edges, and drift tokens.

Prompt templates can be edited without code changes as long as placeholders (`__FILE_EXCERPT__`, `__EVIDENCE_FULL_JSON__`, etc.) remain.

## Related docs

- Maintainer plan: `docs/plans/FILE-COMPARE-LLM-REPORT.md`
- Sample fixture commands: `tests/fixtures/file_compare_llm/README.md`
