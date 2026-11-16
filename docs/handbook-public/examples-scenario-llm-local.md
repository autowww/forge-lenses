---

nav_title: Scenario — local LLM
public_publish: true
audience: public
product_area: lenses
learning_level: overview
section: builders
description: Local-first LLM probe (e.g. Ollama) without exposing API keys in docs
  or tickets.
status: shipped
tier: builder
handbook_area: builders
page_type: topic
---

# Scenario — local-first LLM / Ollama path

## Outcome

Lenses can reach a **local** model endpoint for development; you never paste provider secrets into handbook pages or shared chat.

## Canonical path

[LLM and AI setup](13-llm-and-ai-setup.md) — keep policy boundaries from [Security and local-first](17-security-and-local-first.md) in mind.

## Fixtures

—

## Avoid

- **Shipping** Fleet or cloud keys into sample JSON — use env injection and operator docs only.
