---

nav_title: Diagram catalog (Lenses docs)
public_publish: true
audience: public
product_area: lenses
learning_level: reference
section: resources
status: shipped
description: Approved Kitchen Sink diagram keys for Forge Lenses handbook Markdown.
tier: resource
handbook_area: resources
page_type: topic
---

# Kitchen Sink diagram keys (Lenses docs)

Lenses product docs use **Kitchen Sink** transforms: fenced **` ```blueprint-diagram `**, **` ```blueprint-diagram-expand `**, **` ```blueprint-diagram-ascii `**. Do **not** use Mermaid in `docs/` (workspace policy; KS showcase museum excepted).

Every fence must include meaningful **`alt:`** text and, when helpful, **`caption:`**. Use **`key:`** (or a compatible one-line shorthand) from the catalog in **`kitchensink/js/ks-diagram-catalog.js`**.

| Key | Use in Lenses docs |
|-----|---------------------|
| `linear` | Install, first session, Wizard lifecycle summaries |
| `tree` | Workspace roots, product surfaces |
| `swimlane` | Human / Studio / API / repo responsibilities |
| `decision` | Troubleshooting and security exposure choices |
| `sequence` | Wizard session and trust-boundary flows |
| `state` | Session stages and work item states |
| `network` | Browser, Lenses server, repos, Fleet/LLM |
| `roadmap` | Rollout narratives (use honestly — avoid fake dates) |
| `gantt` | Time-phased plans when grounded in real milestones |
| `heatmap` | Docs Health or coverage summaries (when data-backed) |

CI enforces **known keys** and **`alt:`** via **`scripts/check-docs-diagrams.py`**.

This page satisfies the prompt-pack **`docs/public/reference/diagram-catalog.md`** intent (`docs/handbook-public/` path). When rotating Kitchen Sink revisions, reconcile keys against **`kitchensink/js/ks-diagram-catalog.js`** in the submodule that ships with **`forge-lenses`** so handbook authors and CI share the exact same whitelist.
