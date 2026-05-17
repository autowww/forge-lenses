# Tutorial template (Forge Lenses)

Use this template for **`docs/handbook-public/**` narratives that behave like runnable tutorials rather than glossary entries.

Frontmatter checklist — copy keys from **`docs/NAV-FRONTMATTER.md`** (`nav_title`, `public_publish`, `learning_level`, `tier`, …).

Suggested section order inside the Markdown body:

1. `# Title` describing the observable outcome (“Complete your first Wizard repair pass”).
2. `## Prerequisites` bullets — tools, clones, secrets policy.
3. `## Scenario (no secrets)` or `## Scenario` grounding the persona.
4. `## Steps`, `## Step-by-step`, or `## Procedure` numbering concrete actions.
5. `## Verify` with tables or explicit commands asserting success (**GET-only flows** first).
6. `## Recover` / `## What to do next` / `## Next ladder` bridging to sibling chapters.

Reminder: keep **Kitchen Sink diagrams** fenced as ` ```blueprint-diagram`** with `alt:` + `caption:` (`docs/handbook-public/diagram-catalog-lenses.md`).
