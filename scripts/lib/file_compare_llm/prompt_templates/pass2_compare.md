## Task (Pass 2 — alignment and comparison)

You have Pass-1 understanding for **both** files and full **pairwise evidence**. Align entities/sections and separate stylistic vs material differences.

### Pass 1 — File A
__PASS1A_JSON__

### Pass 1 — File B
__PASS1B_JSON__

### Full evidence pack (deterministic clues)
__EVIDENCE_FULL_JSON__

### Full file text (per excerpt policy)
**File A:**
__EXCERPT_A__

**File B:**
__EXCERPT_B__

### Instructions
Return one JSON object with keys:
- `common_themes` (array of strings): what is genuinely shared
- `aligned_pairs` (array of objects): each has `entity_or_section` (string), `in_file_a` (bool), `in_file_b` (bool), `alignment_note` (string)
- `material_differences` (object) with string values (each 2+ sentences when possible):
  - `scope`, `depth`, `quality`, `completeness`, `consistency`, `clearness`, `domain_fidelity`, `actionability`, `structural_integrity`
- `stylistic_vs_material` (string)
- `missing_in_a` (array of strings)
- `missing_in_b` (array of strings)
