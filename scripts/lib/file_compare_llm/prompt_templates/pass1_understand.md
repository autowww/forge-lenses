## Task (Pass 1 — single file)

Analyze **one** file in isolation. Label: __FILE_LABEL__

### Evidence (deterministic clues only)
__EVIDENCE_SLICE_JSON__

### File text (full UTF-8 content of the file; may match excerpt policy from the CLI / profile)
__FILE_EXCERPT__

### Instructions
Return one JSON object with exactly these keys:
- `file_label` (string): repeat __FILE_LABEL__
- `document_purpose` (string): what this file is trying to do, in plain language
- `intended_audience` (string)
- `major_entities_or_sections` (array of strings): stable names or ids you see
- `themes` (array of strings)
- `strengths` (array of strings, 2–6 items)
- `weaknesses` (array of strings, 2–6 items)
- `domain_drift_hypothesis` (string): whether vocabulary/examples seem off-domain; cite evidence flags if any
- `suggested_quality_dimensions` (array of strings): which quality lenses matter most for this file
