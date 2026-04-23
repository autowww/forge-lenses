# UX / UI Design Versona — §5 report

**Work item:** T5 surface completeness (M1E4–M1E9) — charts, Overview, cockpit vs source, boards, auth clarity  
**Phase:** Specify / Design  
**Review depth:** High  

## Concerns

| # | Concern | Severity | Recommendation |
|---|---------|----------|----------------|
| 1 | Raw JSON and perpetual “Failed to load” train users to distrust the whole workspace. | significant | Primary surface = human summary + “what failed” + recovery; JSON behind an explicit “Technical details” disclosure. |
| 2 | Story Cockpit and Source Context collapsing to the same screen breaks mental models for “plan vs evidence.” | significant | Distinct default tab/panel and page title; one line of context (“You are editing plan…” vs “Inspecting source…”). |
| 3 | Placeholders without “not shipped” semantics read as bugs. | minor | Use explicit deferred copy + link to `docs/roadmap-project-management.md` / WBS row. |

## Evidence requests

- Short task-success list per primary persona (maintainer vs sponsor) for Overview and `/plan`.
- Capture keyboard/focus order for chart error banners and WBS picker.

## Recommendation

**Proceed with conditions** — ship T5 only with defined empty/error patterns and differentiated cockpit vs source IA.
