# Sprint UX4 — Work journey (Plans + Delivery)

## Goal

One mental model: **Work** holds planning and execution. Users move among **Today**, **Plan**, **Boards**, **Timeline**, and **Readiness** without treating “Plans” and “Delivery” as separate products.

## Before → after (journey map)

| Before | After |
|--------|--------|
| Flow breadcrumbs used **Delivery › Today** and **Plans › …** for different surfaces, reinforcing two apps. | Flow breadcrumbs use **Work › …** for plan tabs, boards, timeline, matrix, WBS, and methodology readiness. |
| Work sidebar listed Plan summary before Today and used `from=delivery` on Today. | Sidebar order: **Today → Plan → Boards → Timeline → Readiness**, then matrix, story, sources, WBS, roadmap section, charts. Today has no forced entry hint. |
| In-page bar was a single row mixing summary, story, matrix, WBS, timeline. | **PlanningClusterLocalNav**: primary row **Today · Plan · Boards · Timeline · Readiness**; secondary row **Matrix · WBS · WBS file · Story · Sources** (screen-reader labels for each row). |
| Today (flow) used **DeliveryPageHeader** + separate chrome from Plan summary. | Today uses **PlanningClusterPageHeader** (same chrome as Plan), **CopilotPanel** with a Work-oriented default prompt, and **TechnicalDetails** instead of a loose “Planning context” `<details>`. |
| Scope merge skipped `/board` and readiness URLs. | **`mergePlanningScopeIntoTo`** also carries `repo` / `wbs_p` / `id` / `roadmap_p` into **`/board`** and **`/knowledge/methodology/readiness`**. |
| Contextual rail copy referred to “delivery” and bounced mainly to charts. | Rail actions emphasize **Today ↔ Plan ↔ Boards ↔ Timeline ↔ Readiness** with merged scope; dedicated readiness rail block. |

## Deep links & compatibility

- **`?from=delivery` / `?from=boards`**: Still parsed; copy now says “Linked from …” (legacy param names preserved).
- **URLs unchanged**: `/plan`, `/plan?tab=today`, `/board`, `/timeline`, `/knowledge/methodology/readiness`, etc.
- **Registry parent href** for readiness in flow: first crumb links to **`/plan`** (not a removed route).

## AI / assist

- **Copilot (Today flow)**: Prefill **`WORK_COPILOT_DEFAULT_TODAY`** — variance, blockers, slip, readiness gaps, business-language item summary.
- **Quick assist** (`/plan`): Extra Ask chips for variance, slipping work, readiness gaps, plus boards.

## QA summary (manual)

1. **Work summary**: Open `/plan` (flow) — header, strip, scope bar; breadcrumbs **Work › Plan summary**.
2. **Today**: `/plan?tab=today` — same header family as Plan; strip highlights Today; scope unchanged; copilot prefill present.
3. **Boards**: From Plan with `wbs_p` / `repo` set, open Boards from strip — query carries when merged.
4. **Timeline**: From Today → Timeline — scope preserved via merge.
5. **Readiness**: Strip → readiness; breadcrumbs **Work › Release readiness**; rail returns to Today/Plan/Boards.
6. **Context stability**: `repo`, `wbs_p`, `roadmap_p`, `id` persist across strip navigation where merge rules apply.
7. **Labels**: Primary five are non-overlapping roles (focus / structure / execution / sequence / quality); secondary row is depth tooling (matrix, WBS, story, sources).
8. **Legacy**: Open `/plan?tab=today&from=delivery` — entry hint mentions cross-link, no broken routes.
9. **Blockers / readiness**: Today page still surfaces commitments/blockers cards; readiness page unchanged functionally.
10. **A11y / responsive**: Strip uses `flex-wrap`; row labels are screen-reader-only (`le-glossary-sr-only`); nav has explicit `aria-label` / `aria-labelledby`.

Automated: `npm test` in `lenses-enterprise` (Vitest) after changes.
