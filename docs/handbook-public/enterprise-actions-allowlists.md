---


nav_title: Enterprise — allowlists
public_publish: true
audience: public
product_area: lenses
tier: practitioner
handbook_area: lenses
learning_level: '201'
section: enterprise
status: shipped
description: LENSES_ALLOW_ACTIONS and LENSES_ALLOW_GIT_ACTIONS blast radius.
page_type: concept
---

# Enterprise — actions and tooling allowlists

## What it is

Treat **`LENSES_ALLOW_ACTIONS`** and **`LENSES_ALLOW_GIT_ACTIONS`** as explicit **capability switches** — see [Configuration reference](../reference/config-env.md) and [env matrix](../strategy/env-matrix.yaml).

| Flag | Rough blast radius |
|------|---------------------|
| **`LENSES_ALLOW_ACTIONS`** | Scripted workspace mutations beyond read-only dashboards when paired with authenticated sessions. |
| **`LENSES_ALLOW_GIT_ACTIONS`** | Automation into git + runner **`POST`** flows — audit **`lenses-access.json`** scopes before enabling outside labs. |

Pair flags with **`lenses-access.json`** files checked into repos your operators trust — never expose git/tool runners anonymously.

## Verify

`lenses-access.json` scopes are reviewed **before** flipping either flag outside a lab network.

## What to do next

- [Enterprise — LLM boundaries](enterprise-llm-boundaries.md)
