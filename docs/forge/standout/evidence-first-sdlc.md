---
title: "Evidence-First SDLC"
product: forge-lenses
hydration_source: forge-agentic-sdlc-standout-pack
---

# Evidence-First SDLC

## Core Thesis

Forge's product thesis is evidence-first: the goal is not simply to automate more work, but to create an evidence-producing, human-governed path from intent to decision.

The sharp message is: **the unit of trust is not the agent output; it is the evidence packet.**

## Condensed Thought

AI-generated work becomes useful at scale only when teams can verify it. Forge's architecture makes evidence central. Workcells return reviewable results. Fleet produces execution logs and summaries. LCDL produces governed reasoning traces and validation results. Lenses collects and presents evidence for human review.

This changes the story from "the agent says it is done" to "the run produced evidence that can be reviewed, challenged, and approved."

## Why It Stands Out

A lot of agentic SDLC discussion emphasizes speed: faster code generation, faster review, faster issue handling, faster pull requests. Forge emphasizes decision quality. It asks what evidence a human or governance process needs before trusting the work.

That orientation is especially important for enterprise software delivery. An engineering organization may tolerate experimental agent output, but production delivery needs evidence: tests, diffs, constraints, logs, traces, security checks, architecture notes, and approval records.

## Forge Ecosystem Hooks

- **EvidencePacket** is the core reviewable artifact.
- **Lenses** presents evidence and decision state.
- **Blueprints** define evidence expectations.
- **Versonas** structure discipline-specific review questions.
- **LCDL** produces traceable reasoning and validation artifacts.
- **Fleet** produces execution logs, job summaries, and controlled run output.
- **Workcells** produce results that must be reviewed rather than silently applied.

## Architecture Implications

Evidence-first SDLC requires evidence design as a first-class discipline:

1. Define evidence expectations before execution.
2. Attach every evidence item to a ForgeRun.
3. Distinguish raw artifacts from summarized evidence.
4. Record both successful and failed checks.
5. Preserve enough context for later review without leaking secrets.
6. Make missing evidence visible.
7. Scale evidence requirements with autonomy level and risk.
8. Allow Versonas and Blueprints to define discipline-specific evidence requirements.

Evidence should not be an afterthought generated at the end. It should be part of the run contract.

## Blog Post Seed Paragraph

The phrase "the agent finished" is not enough. In a governed software delivery system, completion must be backed by evidence. Forge treats evidence as the unit of trust. A workcell can draft a patch, Fleet can run a job, and LCDL can reason over the output, but the final decision lives in the evidence packet shown through Lenses. This evidence-first stance reframes agentic SDLC around reviewability rather than raw automation.

## Risks And Counterarguments

Evidence can become noisy. Too many raw logs can overwhelm reviewers. Forge should distinguish between raw artifacts, machine-readable summaries, and human-readable evidence views. The review experience should emphasize relevance, provenance, and decision readiness.

## Related

- [Lenses product boundary](../product-boundary.md)
- [EvidencePacket schema](https://platform.forgesdlc.com/docs-workcells-contracts.html)
