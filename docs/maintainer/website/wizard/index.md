# Blueprints Wizard — guides

The **Blueprints Wizard** is an **experimental**, Forge Studio–only guided flow. It helps you turn intent into a **foundation brief**, structured understanding, **targets and scope**, a **run plan**, and generated **artifacts**—without editing the `blueprints/` git submodule in your workspace. You run it from **`/studio/blueprints/wizard/`** on your local Lenses server.

## Prerequisites

1. **Lenses** running (`python3 -m lenses` or your usual script) with Forge Studio available at **`/studio/`**.
2. **Server-enabled wizard** (default on). If the Studio app cannot reach the wizard APIs, it falls back to a **local-only draft** stored in the browser—useful for quick notes, but not a full session on disk.
3. Optional: **LLM** features (refine, interpret, artifact generation) follow the same trust rules as the rest of Lenses chat (typically **loopback** unless you have explicitly allowed actions for your bind).

## Progressive guides

| Guide | Who it’s for | What you’ll learn |
|-------|----------------|-------------------|
| [Wizard 101 — Getting started](wizard-101-getting-started.md) | First-time users | Hub vs session, the twelve steps end-to-end, one worked example (“start from idea”) |
| [Wizard 201 — Mission modes and scenarios](wizard-201-mission-modes.md) | Teams mapping work to Forge | The four mission modes with realistic scenarios, hub vs session, server vs local |
| [Wizard 301 — Advanced usage](wizard-301-advanced-usage.md) | Power users | Artifact bundles, refining with the LLM, Cursor Launch Pack, GitHub repo creation, troubleshooting |

## Related

- [User guide home](../home.md) — Lenses and Forge Studio overview
- [Interface pages](../interface-pages.md) — Classic vs Studio and navigation
- Maintainer / operator details remain in the forge-lenses repo (not on this site): `docs/blueprints/wizard-usage.md`, architecture, domain model, file map.
