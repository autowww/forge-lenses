## Task (Pass 3 — scores and human-facing summary)

Use Pass 1 and Pass 2 outputs plus the **evidence** as inputs. **You** assign 0–100 scores per file per dimension (integer). Evidence informs judgment but does not replace it.

### Pass 2 JSON
__PASS2_JSON__

### Evidence (reminder)
__EVIDENCE_FULL_JSON__

### Dimension labels (for scorecard "why it matters")
__DIMENSIONS_TABLE_MD__

### Instructions
Return one JSON object with keys:
- `executive_summary_bullets` (array of 5–8 strings): must cover, in plain language: what the two files are; what is common; what is materially different; which file is stronger overall; which is more trustworthy editorially/semantically; which is more operationally usable; bottom-line recommendation
- `scorecard` (array of objects): each has `dimension_id` (string, one of: structural_integrity, scope, domain_fidelity, consistency, clearness, depth, actionability, overall), `file_a` (int 0-100), `file_b` (int 0-100), `winner` ("A"|"B"|"Tie"), `why_it_matters` (string, one sentence)
- `scores_justification` (object): keys `file_a` and `file_b`, each an object mapping dimension_id to a short string rationale referencing evidence when useful
- `what_is_common` (array of strings): bullets for "## What is common"
- `entity_deltas` (array of objects): each with `entity`, `common_ground`, `difference`, `why_it_matters`, `preferred_version` ("A"|"B"|"Tie")
- `human_bottom_line` (string): non-technical paragraph tying differences to scores
- `appendix_notes` (string, optional): brief note on how deterministic clues influenced (not dictated) scores

Every dimension_id in scorecard must appear exactly once.
