# AI Setup — block contract (Model sources)

This document defines what each **density** mode shows for every block in **Model sources**. Density is persisted in the browser (`AiSetupSourceLayoutV2`). **Cloud** vendors and **More providers** use **per-tile** density (`cloudTileDensity`). **Custom** and **Ollama** use **one** density per section (`customTileDensity`, `ollamaTileDensity`).

| Mode | Meaning |
|------|---------|
| **Tile** (`compact`) | Read-only summary: status, one-line model, try result, route chips where applicable. No API keys, no comboboxes, no discover/health (cloud tiles expose **Expand to configure**; custom/Ollama rely on the **section** density control). |
| **Hero** | Full configure surface for that block: credential/manage flows, model selection where supported, **Test** / **Discover** / **Health**, **Used for** chips. |
| **Advanced** | Everything in **Hero** plus **Ollama-style** in-lane diagnostics: recent chat events, **Discover / Health** probe history from `llm-usage.json`, longer model strips, and (custom gateway) aggregated **GET /api/llm/diagnostics** row for `openai_compatible`. Full tables and **Usage & diagnostics** remain at the bottom of the page. |

## Per-provider matrix

| Provider id | Tile | Hero | Advanced |
|-------------|------|------|----------|
| `openai`, `anthropic`, `gemini` | Status pill, model id line, try result, used-for text, optional catalog preview line, **Expand to configure** | Outcome blurb, credential hint, full chips, probe strip, actions + manage key | Hero + recent events + probe log slices + advanced hint |
| `more_providers` | Title, shortcut hint, **Expand shortcuts** | Description + shortcut buttons (custom / Ollama) | Same as hero (copy / actions scale with density) |
| `openai_compatible` (custom card) | Status, endpoint preview, model id line, try result, chips; **Add / Edit custom provider** only | Non-compact: combobox, hints, all actions | Hero + diagnostics row from `/api/llm/diagnostics` + recent chat + probe list + hint |
| `ollama` | Host one-liner, status, default model line, try result, library count + chips; note to use section density | Full `OllamaLocalPanel`: roles, catalog table or disclosure, pull/actions | Full catalog table, setup script, all actions |

## References (code)

- Cloud blocks: `src/components/ai-setup/CloudSwimlaneBlocks.tsx` (`CloudVendorCard`, `CloudMoreProvidersCard`).
- Custom gateway: `OpenAiCompatGatewayPanel` in `src/components/LlmSettingsForm.tsx`.
- Ollama: `src/components/ai-setup/OllamaLocalPanel.tsx`.
- Layout persistence: `src/components/ai-setup/aiSetupSourceLayout.ts`.
