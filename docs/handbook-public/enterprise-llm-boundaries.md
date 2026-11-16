---


nav_title: Enterprise — LLM
public_publish: true
audience: public
product_area: lenses
tier: practitioner
handbook_area: lenses
learning_level: '201'
section: enterprise
status: shipped
description: Local vs hosted LLM routing and data-handling expectations.
page_type: concept
---

# Enterprise — LLM provider boundaries

## What it is

| Provider style | Guidance |
|----------------|----------|
| **Local Ollama / LM Studio** | Preferred for proprietary repos — prompts stay on-disk beside your workspace. |
| **OpenAI-compatible proxies** | Ensure TLS + tenant isolation when routing outside **`127.0.0.1`**. |
| **Hosted APIs** | Verify data-processing agreements — Wizard refine payloads may contain methodology snippets from local repos. |

Credential storage paths live under **[Configuration reference](../reference/config-env.md)**.

## Verify

No production secret appears in handbook examples or shared chat — env injection only.

## What to do next

- [LLM and AI setup](13-llm-and-ai-setup.md)
