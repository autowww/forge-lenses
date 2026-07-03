---
title: "Versonas as Callable Discipline Lenses"
product: forge-lenses
hydration_source: forge-agentic-sdlc-standout-pack
---

# Versonas as Callable Discipline Lenses

## Core Thesis

Versonas are one of ForgeSDLC's most original concepts: they turn professional disciplines into callable lenses that can be invoked at decision points. They are not just personas and not replacements for accountable humans.

The core phrase is: **Versonas are discipline lenses, not org roles.**

## Condensed Thought

Software delivery requires many perspectives: product, architecture, security, testing, DevOps, UX, compliance, business analysis, and more. In traditional SDLCs, those perspectives live in people, meetings, checklists, review templates, and organizational habits. ForgeSDLC codifies them as Versonas that can guide humans and agents.

A Versona can structure the questions asked of a change, the evidence required, the risks examined, and the decision criteria applied. Humans remain accountable for binding decisions, but the discipline lens becomes reusable and invokable.

## Why It Stands Out

The idea moves beyond generic "AI reviewer" behavior. Instead of asking an agent to review code in a vague way, Forge can ask a security Versona, testing Versona, architecture Versona, or UX Versona to examine the run through a specific discipline lens.

This has two benefits. First, it makes review more consistent. Second, it gives agents better context than raw prompts because the review frame is grounded in ForgeSDLC vocabulary, Blueprints policy, and evidence expectations.

## Forge Ecosystem Hooks

- **ForgeSDLC** defines the methodology and Versona concept.
- **Blueprints** hold canonical Versona artifacts and policy expectations.
- **Lenses** can surface Versona-guided evidence and reviews.
- **LCDL** can run governed reasoning using Versona-shaped contracts.
- **Workcells** may include versona_runner types for discipline-lens review.
- **EvidencePacket** can include Versona findings and decision support.

## Architecture Implications

To make Versonas useful as architecture primitives:

1. Each Versona should have a clear discipline scope.
2. Versona prompts and policies should be versioned.
3. Versona outputs should be structured enough to become evidence.
4. Versona findings should separate observations, risks, recommendations, and required gates.
5. Human accountability should be explicit: the Versona informs, the human decides.
6. Versona behavior should be testable against sample runs.
7. Multiple Versonas should be composable without creating noisy review conflict.

## Blog Post Seed Paragraph

A persona describes a user. A Versona describes a professional lens. ForgeSDLC uses Versonas to make disciplines callable inside the delivery flow. Instead of relying on a generic agent to "review the change," a run can invoke architecture, security, testing, UX, or product lenses that know what to look for and what evidence matters. The Versona does not replace accountability. It structures judgment so humans and agents can reason more consistently.

## Risks And Counterarguments

The risk is anthropomorphizing Versonas or overstating their authority. Forge should keep the language precise: Versonas are structured review lenses and decision aids. Humans remain accountable for binding decisions, especially where risk, policy, or product judgment is involved.

## Related

- [Lenses product boundary](../product-boundary.md)
- [EvidencePacket schema](https://platform.forgesdlc.com/docs-workcells-contracts.html)
