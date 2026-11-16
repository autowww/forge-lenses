# File compare LLM — test fixtures

Small JSON and text files used by `tests/test_file_compare_llm_*.py`.

## Regenerate a local Markdown sample (no LLM)

From the **forge-lenses** repo root:

```bash
python3 scripts/compare_files_llm_report.py --deterministic-only \
  --a tests/fixtures/file_compare_llm/fragments_dup_drift.json \
  --b tests/fixtures/file_compare_llm/fragments_wrapped_broken_ref.json \
  --out-dir /tmp/file-compare-sample --basename comparison_report
```

Outputs `comparison_report.md` and `comparison_report.json`. Paths inside the JSON appendix are absolute on your machine; do not commit that output unless you redact paths.
