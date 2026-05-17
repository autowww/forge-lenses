---


nav_title: Enterprise — OIDC
public_publish: true
audience: public
product_area: lenses
tier: practitioner
handbook_area: lenses
learning_level: '201'
section: enterprise
status: shipped
description: OIDC sign-in, reverse proxies, and governance POST discipline.
page_type: concept
---

# Enterprise — OIDC and reverse proxies

## What it is

Enterprise builds can pair **OIDC** sign-in with **`lenses-access.json`** RBAC. Keep loopback binding until the proxy terminates TLS and injects identity headers deliberately.

Telemetry and governance **`POST`** endpoints still honor local-first defaults. Historical governance decisions (audit logging, bearer flows)—including the material summarized as **ADR 013** for contributors—are indexed from the **[Maintainer handbook on GitHub](https://github.com/autowww/forge-lenses/blob/main/docs/maintainer/index.md)**; this public handbook avoids deep-linking individual ADR files.

## Environment

OIDC-related **`LENSES_OIDC_*`** variables are summarized in [Configuration reference](../reference/config-env.md) and flagged in [env matrix](../strategy/env-matrix.yaml).

## Verify

Login completes without redirect loops and **`/api/auth/status`** reflects the expected session when exercised through the same hostname operators publish.

## What to do next

- [Enterprise — actions allowlists](enterprise-actions-allowlists.md)
