---

nav_title: Glossary
public_publish: true
audience: public
product_area: lenses
learning_level: overview
section: resources
description: Short definitions for Forge Lenses, Studio, Wizard, and local-first storage.
status: shipped
tier: resource
handbook_area: resources
page_type: reference
---

# Glossary

| Term | Meaning |
|------|---------|
| **Classic Lenses** | Legacy HTML dashboard served by `python3 -m lenses` at `/` (not `/studio/`). |
| **Forge Studio** | React SPA at `/studio/` (`lenses-enterprise`) sharing `/api` with Classic. |
| **Blueprints Wizard** | Guided multi-step flow inside Studio; does **not** auto-edit the Blueprints submodule. |
| **Workspace root** | Directory Lenses scans for repos; see [Workspace setup](03-workspace-setup.md). |
| **`.lenses-local/`** | Per-workspace state: Wizard sessions, FTS index, telemetry — see [Security](17-security-and-local-first.md). |
| **`.lenses-repo/`** | Cached GitHub overlays once PAT sign-in succeeds. |
| **Docs Health** | Job + UI for documentation quality signals ([chapter](15-docs-health.md)). |
| **Kitchen Sink diagram** | Product docs use `blueprint-diagram*` fenced blocks (not Mermaid). |
