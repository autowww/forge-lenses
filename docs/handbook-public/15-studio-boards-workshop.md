# Studio boards workshop

Forge Lenses **Sticker boards** in **Studio** (`/studio/board`) support facilitated workshops: roadmap sessions, product map layout, and impact/effort prioritization.

## Before the session

1. Open Studio from a running Lenses server (`http://127.0.0.1:8080/studio/`).
2. Ensure the workspace scan succeeded (boards hub loads without a registry error).
3. For **product map** prefills, the project needs `docs/requirements/WBS.md` (or another WBS path detected by the workspace scan).

## Create a board

| Template | Use when |
|----------|----------|
| **Product map workshop** | You want stickers seeded from the project WBS (epics → capabilities, stories → journey). |
| **Roadmap session** | Horizon columns: Now / Next / Later / Parking. |
| **Executive review** | Decide / Discuss / Defer / Risks. |
| **Dependency mapping** | Freeform canvas for cross-team dependencies. |
| **Architecture decision** | Options / Tradeoffs / Decision. |
| **Workshop kickoff (Markdown)** | Product validation workshop from a kickoff `.md` (decisions, feature map, agenda, journey). |

Use **Create from project** on the product map card to pick the workspace child (repo folder name).

Use **Import Markdown** on the workshop kickoff card to pick a `.md` file from disk (or create via API with `workshop_md_path` / `workshop_md_text`).

## Workshop kickoff Markdown conventions

Kickoff docs should use `##` sections so Lenses can seed stickers:

| Section heading (contains) | Board column | Sticker content |
|----------------------------|--------------|-----------------|
| **Workshop validation board** | Discuss | One card per table row (decision + options + empty team decision) |
| **Feature map for validation** | Discuss | One card per feature area |
| **Suggested … agenda** | Reference (Parking) | One card per `###` time block (goal, prompt, decisions) |
| **Main product journey** | Discuss | Journey stages from table or `Home → …` fenced text |
| Other `##` sections | Reference | Section anchor (summary excerpt) |

Optional YAML frontmatter:

```yaml
---
lenses_workshop:
  label: "A11y Studio kickoff"
  project: forge-accessibility-leo
  default_phase: discover
---
```

Save a copy under the workspace (e.g. `ember-logs/workshop-kickoff.md`) if you want it in **Workspace notes** alongside the board.

### Facilitator flow (90-minute product kickoff)

1. **Discover** — Walk agenda reference cards; arrange journey and feature stickers in **Discuss**.
2. **Score** — Set impact/effort on feature-area cards.
3. **Prioritize** — Drag features into **Core MVP**, **Support**, **Proof / direction**, or **Later**; sort by priority if helpful.
4. **Capture** — Move validation decisions to **Decided**; record outcomes in [Workspace notes](/studio/workspace-md) or [Plan](/studio/plan).

Remote participants can use guest **Stickerboard** sharing (see handbook §16).

## Workshop phases

1. **Discover** — Arrange stickers on the kanban canvas (drag-and-drop).
2. **Score** — Set **Impact** and **Effort** (1–5) on each card.
3. **Prioritize** — Enable **Sort by priority** (impact ÷ effort).
4. **Capture** — Record outcomes in [Workspace notes](/studio/workspace-md) or continue in [Plan](/studio/plan) for the same repository.

## Registry hygiene

If the hub lists **Registry issues**, use **Fix registry** to drop missing files and correct storage flags.

## API (automation)

`POST /api/sticker-board-registry` with:

```json
{
  "action": "create",
  "payload": {
    "project": "forge-lenses",
    "label": "Q2 roadmap",
    "storage": "local",
    "session_template": "roadmap_session"
  }
}
```

Product map with prefill:

```json
{
  "action": "create",
  "payload": {
    "project": "forge-lenses",
    "label": "Product map",
    "session_template": "product_map_workshop",
    "prefill": true
  }
}
```

Workshop kickoff from Markdown (path under workspace root):

```json
{
  "action": "create",
  "payload": {
    "project": "forge-accessibility-leo",
    "label": "A11y Studio kickoff",
    "session_template": "workshop_kickoff",
    "workshop_md_path": "ember-logs/a11y_studio_product_workshop_kickoff.md",
    "prefill": true
  }
}
```

Or pass `workshop_md_text` with the full file body (Studio file import uses this).

PDCA prompt pack: `scripts/studio-boards-workshop-pdca/run-boards-workshop-pdca.sh`. Parser tests: `pytest tests/test_board_workshop_md.py`.
