# Sprint UX2 — Progressive disclosure & page anatomy (Forge Studio)

## Standards (shared primitives)

| Primitive | Role |
|----|---|
| **`PageHeader`** (`components/page/PageHeader.tsx`) | Title, optional **purpose** (one line), **freshness**, **statusChips**, **primaryAction**, **secondaryMenuItems** (overflow), legacy **`actions`** cluster, optional **`subtitle`**. |
| **`PageSummaryBand`** | First body band after the header (KPIs, “next steps”, paired summaries). |
| **`TechnicalDetails`** | Collapsed-by-default block for endpoints, paths, raw JSON, session fields, expert forms. |
| **`PageAiInsightCard`** | Compact “what changed / why / next” supportive card (not visually dominant). |
| **`PageHeaderActionsMenu`** | Overflow menu used by `PageHeader` for secondary destinations. |

### Page flow (recommended)

1. Header (title → purpose → primary action).  
2. Optional **PageAiInsightCard**.  
3. **PageSummaryBand** — snapshot / next steps / key metrics.  
4. Deeper panels and cards.  
5. **TechnicalDetails** — debug, APIs, raw payloads.

### Planning cluster

- **`PlanningClusterPageHeader`** — title row + optional **actions**; registry subtitle as **purpose**; entry hints in **TechnicalDetails** (“Planning entry context”).
- **`DeliveryPageHeader`** — purpose line + primary link to plan summary; Today vs plan / classic workspace copy in **TechnicalDetails**.

### Right rail (`EvidenceRail`)

- **Developer / raw data** links (e.g. raw workspace JSON) moved under **TechnicalDetails**.
- **`showLead: false`** on Search and Copilot routes so the rail stays status + next steps without repeating long prose.
- Knowledge cluster title set to **“Knowledge & reference”** with a shorter lead.

## Pages updated (minimum set)

- **Home** — new header anatomy, **PageAiInsightCard**, **PageSummaryBand**, directory + raw JSON → **TechnicalDetails**.
- **Plan (Flow)** — trace action in header toolbar; classic links / repo shortcut in **TechnicalDetails**; raw JSON blocks use **TechnicalDetails**.
- **Plan (Artifacts)** — lens hint in **TechnicalDetails**.
- **Today / Delivery** — simplified header + progressive disclosure for lens/classic copy.
- **Project overview** — primary **Charts**, overflow for strategy / evidence / classic; session meta in **TechnicalDetails**; summary band for next steps + evidence CTA.
- **Search** — purpose + AI card + repo scope in **TechnicalDetails**; rail lead suppressed.
- **Copilot / Chat** — purpose + chips + primary **AI Setup**; legacy chat block in **TechnicalDetails** (`defaultOpen` when Copilot off).
- **Workspace markdown** — purpose + demo trace + expert path loader + raw source → **TechnicalDetails** / disclosure patterns.
- **Tutorials** — API discovery line → **TechnicalDetails**.
- **Websites (Publish)** — shorter header; classic `/websites` explanation → **TechnicalDetails**.

## QA summary

| Check | Result |
|----|-----|
| Automated tests | `npm test` — 354 passed |
| Production build | `npm run build` — OK |
| Heading hierarchy | Pages keep a single document **h1** in the shared header; subsections use existing **h2** patterns. |
| Landmarks | **`PageHeader`** uses `role="region"` + `aria-labelledby`; **`PageSummaryBand`** uses `role="region"`; overflow menu **`role="menu"`** / **`menuitem`**. |
| Keyboard | **TechnicalDetails** uses native `<summary>`; overflow and rail collapse remain keyboard-reachable. |
| Visual regression | Not run in CI; spot-check header spacing and rail on home, plan, project, search, chat. |

### Manual pass (recommended)

1. Each updated page: confirm **purpose** reads clearly; **primary** action is obvious.  
2. Open every **TechnicalDetails** / rail **Developer** block: content hidden by default, expands predictably.  
3. Resize to ~768px: header toolbar wraps without clipping overflow menus.  
4. Search + Chat: confirm contextual rail shows **no** long lead paragraph.
