---

nav_title: Scenario — root vs submodule
public_publish: true
audience: public
product_area: lenses
learning_level: overview
section: builders
description: Choosing a standalone clone layout versus embedding blueprints or kitchensink
  as submodules.
status: shipped
tier: builder
handbook_area: builders
page_type: topic
---

# Scenario — standalone clone vs submodule layout

## Outcome

You pick a **root** Lenses should treat as authoritative for scans and docs policy, understanding how submodules appear compared with a flat sibling tree.

## Canonical path

[Workspace setup — root choice](03-workspace-setup_02-root-choice.md) explains trade-offs; pair with [Layouts](03-workspace-setup_01-layouts.md) for physical directory shape.

## Fixtures

— (layout and git submodule pointers vary by org)

## Avoid

- Editing **read-only submodule copies** inside a consumer repo without promoting changes to the standalone upstream (workspace submodule rules).
