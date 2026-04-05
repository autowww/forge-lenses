# Lenses Studio — Flow lens shell (MVP scope)

**Decided MVP (product engineering):**

- **In scope:** Universal **Studio shell** on every `/studio/` route: context bar (scope, time horizon, compare, saved view placeholder, filters placeholder), executive KPI strip, attention stream (exception-style items derived from existing workspace data), and evidence + actions rail (links to docs, tutorials, workspace evidence, workspace JSON API). **Navigation copy** for Flow and Artifacts lenses uses plain-language labels; **side nav** removes disabled stubs in favor of real destinations or focused link sets.
- **Out of scope for this MVP:** Per-section bespoke landing modules (PortfolioPulse heatmap, CommitmentDelta, full ranked news pipeline, dependency graph, initiative layer, publish-parity automation). Those follow once APIs and product signals exist.
- **Home:** The workspace overview route remains the primary drill-down for the portfolio table; KPIs in the shell avoid duplicating the full child table while surfacing portfolio-level counts and freshness.

This document satisfies the “validate scope” checkpoint for the enterprise shell redesign without blocking on external stakeholder review.
