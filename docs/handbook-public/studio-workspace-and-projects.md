---


nav_title: Studio workspace and projects
public_publish: true
audience: public
product_area: studio
tier: practitioner
handbook_area: studio
learning_level: '201'
section: studio-wizard
description: Home, projects, charts, strategy, and embedded doc viewers in Forge Studio.
status: shipped
page_type: topic
---

# Studio — workspace and projects

## What it is

The **Home** area covers **overview/charts**, **projects** list, **per-project** routes (`projects/:name`, charts, **strategy**), and **Docs Health** subtrees under a project — see tokens in the [route atlas](14-studio-route-map.md) **Home** row.

## When to use it

Daily **portfolio review**: scan project rows, drill into **one** product, then open **strategy** or **docs-health** when hygiene signals matter.

## Embedded viewers

Studio serves selected static previews via **`view/docs/*`**, **`view/local-site/*`**, **`workspace-md`**, and **`workspace-md/view`** (see atlas **Embedded** row). Treat these as **same-origin** readers — they still rely on the workspace scan configured in [Workspace setup](03-workspace-setup.md).

## Docs Health under a project

Routes like **`projects/:name/docs-health`** and **`.../session/:sessionId`** surface the same JSON families described in [Docs Health overlays](15-docs-health.md); start with the **[Docs Health UI](studio-docs-health-ui.md)** page when coaching operators.

## Verify

Pick **one** project from the list; its detail URL should include the **slug** you expect and load charts or strategy without console errors referencing a **foreign API origin**.

## What to do next

- [Studio 201](06-studio-201.md)
- [Studio route atlas](14-studio-route-map.md)
