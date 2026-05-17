---


nav_title: Studio LLM and Fleet settings
public_publish: true
audience: public
product_area: studio
tier: practitioner
handbook_area: studio
learning_level: '201'
section: studio-wizard
description: Settings routes for LLM gateway, Forge Fleet jobs, and related Studio experiments.
status: shipped
page_type: topic
---

# Studio — LLM and Fleet settings

## What it is

**Settings** in Studio includes **`settings/llm`**, **`settings/fleet`**, **`settings/ux-insights`**, and **`settings/agent-runtime`** (tokens from [Studio route atlas](14-studio-route-map.md)). These panes **configure** how Studio calls **local or remote** model gateways and **Fleet** orchestration — they do not replace server-side env from [Configuration reference](../reference/config-env.md).

## When to use it

- After [LLM and AI setup](13-llm-and-ai-setup.md) when you need the **Studio UI** to match CLI-probed endpoints.
- When jobs fail in **`/api/`** families tied to Fleet — confirm **settings/fleet** matches operator intent before escalating.

## Boundaries

- **Operator truth** for bind addresses and secrets remains **[Security and local-first](17-security-and-local-first.md)** + `LENSES_*` reference.
- **Builder automation** must stay on documented **`GET`**/`POST` tables in [Schemas and API for builders](16-schemas-and-api-for-builders.md).

## Verify

Visit **`settings/llm`** and save or reload; Network tab calls should target your **Lenses origin** (see [Studio troubleshooting](studio-troubleshooting.md) if they do not).

## What to do next

- [LLM and AI setup](13-llm-and-ai-setup.md)
- [Studio route atlas](14-studio-route-map.md)
