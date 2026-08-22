# Sprint UX3 — Unified command bar & embedded Copilot (Forge Studio)

## Goal

One lightweight **Find | Ask | Do** surface (header + **⌘/Ctrl+K**) replaces duplicative “search box + separate destinations” as the primary workflow. **`/search`** and **`/chat`** remain **advanced** full pages.

## What shipped

| Area | Behavior |
|------|------------|
| **Command bar** | Modal (`StudioCommandBar.tsx`): **Find** (nav + contextual suggestions + `/api/search` when query ≥ 2 chars), **Ask** (single-turn grounded `/api/sdlc-copilot/chat`, **read-only**), **Do** (safe navigate + **draft preview / copy only** — no silent writes). |
| **Global shortcut** | **Ctrl+K / ⌘+K** opens Find (handled in `StudioCommandBarProvider`; removed old “focus header search field” behavior). |
| **Header** | `HeaderUtilities`: **Find / Ask / Do** buttons open the bar in the matching mode; **Find anything…** trigger replaces the old inline search field; **Copilot** opens **Ask**. |
| **Context** | `buildContextualCommands.ts` powers suggestions and Do actions from **pathname** + optional **project** segment. |
| **Recents** | `localStorage` key `lenses.studio.cmdRecent` — last navigations from Find results. |
| **Inline assist** | `StudioInlineAssist.tsx` on **Home**, **Plan** (Today + summary + artifacts), **Project**, **Workspace MD**, **Websites** — chips open **Ask** with prefilled text or **navigate**. |
| **Advanced pages** | Banners on **Search** and **Chat** explain they are full/advanced modes vs the command bar. |
| **Telemetry** | `recordCommandBar` / `recordCommandBarAskFailure`; aggregates **`commandBarActions`** and **`commandBarAskFailures`** in `getStudioTelemetrySnapshot()`; **UX insights** page lists them. |

## Find / Ask / Do — example flows

1. **Find — jump to Today**  
   Press **⌘K** → stay on **Find** → type `today` → choose **Today** (or **Open Today** in Do) → navigates to `/plan?tab=today`.

2. **Find — indexed hit**  
   Type two or more characters → wait briefly → API hits appear under nav/suggestions → pick row → navigates or opens external URL.

3. **Ask — grounded question**  
   Header **Ask** or **Copilot** → type “What readiness gaps should I check?” → **Ask** → response lists **citations** when the server returns them; **Router links** for `ref` values starting with `/`.

4. **Ask — no citations**  
   If the model answers but sends no citations, UI shows a **partial-context** note and telemetry **`ask_no_citations`**.

5. **Do — safe navigate**  
   **Do** mode → **Open boards** → navigates (no confirmation needed).

6. **Do — draft preview**  
   **Draft daily brief** or **Stakeholder update** (on publish surfaces) → **preview modal** → **Copy to clipboard** only (operator-controlled “write”).

## Guardrails

- Ask mode always sends **`tool_mode: 'read_only'`** from the command bar.  
- Do mode does **not** call `commit-proposal` or other writes — only **navigate** or **copy** after explicit preview.  
- Failed Ask turns increment **`commandBarAskFailures`** keyed by trimmed query (for UX insights review).

## QA summary

| # | Check | Result |
|---|--------|--------|
| 1 | Find / Ask / Do modes render and switch | Manual: OK |
| 2 | **⌘/Ctrl+K** opens bar; **Esc** closes | OK |
| 3 | Suggestions change with route (e.g. project vs home) | OK |
| 4 | Citations with `/` refs render as `<Link>` | OK |
| 5 | Do never auto-writes | Only navigate + copy preview |
| 6 | Empty / error Ask states show banner + failure telemetry | OK |
| 7 | `/search` and `/chat` still load as advanced destinations | Banners + footer links in bar |
| 8 | Dialog: `role="dialog"`, `aria-modal`, labelled title | OK (light focus management; full roving tabindex not implemented) |
| Automated | `npm test` | 355 passed |
| Build | `npm run build` | OK |

## Follow-ups (optional)

- Roving **`aria-activedescendant`** / arrow keys for Find results.  
- Share more logic with **`CopilotPanel`** (e.g. reuse a small `useCopilotProvider` hook).  
- E2E test opening the bar and selecting a nav result.
