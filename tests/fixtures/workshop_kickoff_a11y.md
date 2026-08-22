# Forge A11y Studio — Product Workshop Kick-off

## Executive summary

**Forge A11y Studio is a local-first accessibility control workbench.** Its purpose is to help teams move from scattered accessibility checks to a governed operating model: know what digital resources exist, run evidence-backed audits, review findings with human accountability, guide engineering fixes, monitor regressions, and publish stakeholder-ready reports.

The product should not be positioned as “another scanner.” The value is the full control loop around accessibility evidence:

**Inventory → Start audit → Audit results → Review findings → Fix & verify → Monitor → Reports.**

The archive shows a strong technical foundation: a desktop Electron shell, local Python service, Playwright/Chromium accessibility evidence, axe-based automated rule checks, persisted artifacts, run history, structured findings, registry/inventory, expert review, WCAG mapping, remediation handoff, traceability, monitoring, and reporting. The current risk is that the UI exposes too much implementation detail too early: route IDs, artifact filenames, API/source language, raw engine names, dense cards, small muted text, repeated phrases, and unclear navigation. This makes the product feel complicated before the value is understood.

The workshop goal is to align the team around the product story and feature priorities before further redesign and implementation. The redesign should simplify the experience around one core promise:

> **A11y Studio gives teams a clear, evidence-backed path from accessibility risk to accountable action.**

The key workshop decisions are:

1. Who is the primary user for the first release: accessibility consultant, product owner, engineering lead, QA lead, or internal governance owner?
2. What is the first valuable end-to-end workflow: audit evidence, expert review, engineering handoff, monitoring, or stakeholder reporting?
3. What must be live and trustworthy now versus clearly labeled sample/roadmap capability?
4. Which product terms become canonical: Inventory, Start audit, Audit results, Review findings, Fix & verify, Monitor, Reports.
5. What proof will make the product credible: saved evidence, reviewed findings, traceable remediation, regression monitoring, or executive-ready reports?

## Workshop purpose

This kick-off is not a UI critique session only. It is a product validation session.

The team should leave with a shared answer to five questions:

1. **What problem does A11y Studio solve?**
2. **Who is it for first?**
3. **What is the main product journey?**
4. **Which features are core, which are supporting, and which are future?**
5. **What must change in the UX so the value is obvious within the first minute?**

## One-line product positioning

**Forge A11y Studio is a local-first accessibility control workbench that turns audit evidence into reviewed findings, engineering-ready fixes, monitoring signals, and governed reports.**

## Plain-language product promise

Accessibility teams do not only need more findings. They need confidence that every issue has:

- a known resource and owner;
- evidence that can be inspected;
- a reviewed decision, not just an automated guess;
- a clear fix path for engineering;
- verification and regression monitoring;
- a report that explains risk without exposing raw technical noise.

A11y Studio should become the place where that chain is visible and actionable.

## The product story

### 1. The old world

A product team wants to improve accessibility. They run a scanner, get a long list of issues, export some files, open tickets manually, and ask experts to validate what matters. Evidence lives in different places. WCAG mappings are uncertain. Engineers receive vague handoff notes. Regression checks happen late, if at all. Leadership sees risk summaries that are disconnected from the underlying evidence.

The result is familiar:

- accessibility work feels reactive;
- teams debate findings instead of fixing problems;
- evidence gets lost between audit, review, and delivery;
- ownership is unclear;
- progress is hard to prove;
- compliance conversations happen without a reliable trace.

### 2. The new world

A11y Studio starts with the resources the team owns. It lets the user launch a governed audit and saves the evidence package locally. Automated checks and browser accessibility evidence become candidate findings, not final truth. An expert reviews, confirms, rejects, or marks items for manual testing. Confirmed issues move into Fix & verify, where the team captures owner, acceptance criteria, retest steps, and approval. Monitoring watches for drift and regressions. Reports package the reviewed story for executives, consultants, and engineering teams.

The product turns accessibility from a one-time scan into a governed operating loop.

### 3. The reason this matters

The value is not simply finding defects. The value is reducing ambiguity:

- **For accessibility experts:** less time reconstructing evidence and more time making decisions.
- **For product owners:** clearer view of risk, scope, and next action.
- **For engineering:** fix instructions with acceptance criteria and retest expectations.
- **For QA:** evidence and verification steps connected to findings.
- **For leadership:** reports that distinguish reviewed facts from draft automation.

### 4. The product principle

**Automation assists. Experts decide. Evidence travels with the decision.**

This principle should drive the UX, the feature model, and the workshop decisions.

## Product value pillars

| Value pillar | Meaning | Product proof |
|---|---|---|
| **Local-first trust** | Sensitive audit data stays on the machine by default. | Desktop Studio, local service, local artifacts, explicit data boundaries. |
| **Evidence-backed work** | Every recommendation should connect to inspectable evidence. | Audit artifacts, browser accessibility evidence, automated rule checks, previews/downloads. |
| **Human-governed decisions** | Automation is draft until reviewed. | Expert review states, WCAG confirmation, approval gates. |
| **Actionable handoff** | Engineering receives fix-ready work, not vague scan output. | Owner, acceptance criteria, retest steps, handoff readiness, markdown export. |
| **Traceability** | Teams can explain how a finding moved from evidence to fix and verification. | Resource → evidence → WCAG → test case → owner → remediation → verification chain. |
| **Regression control** | Accessibility should not decay silently after release. | Monitoring baselines, drift signals, alerts, comparison views. |
| **Stakeholder clarity** | Reports should explain risk and confidence without raw technical clutter. | Publication readiness, provenance, reviewed/draft/approved labels, executive summaries. |

## Main product journey to validate

The proposed canonical journey is:

```text
Home → Inventory → Start audit → Audit results → Review findings → Fix & verify → Monitor → Reports
```

Each stage should answer one user question:

| Stage | User question | Expected primary action |
|---|---|---|
| **Home** | What needs my attention today? | Open the most important next action. |
| **Inventory** | What resources do we own and audit? | Add/link resources or review coverage gaps. |
| **Start audit** | What am I auditing, and what evidence will be saved? | Start a governed audit. |
| **Audit results** | Which audit result should I open, and what happened? | Choose an audit result or try a sample result. |
| **Review findings** | Which findings need expert judgment? | Review candidate findings. |
| **WCAG review** | Which mappings need confirmation? | Confirm or adjust suggested mappings. |
| **Fix & verify** | What must engineering fix, and how do we verify it? | Prepare or approve handoff. |
| **Monitor** | What changed since baseline? | Review drift or regression alerts. |
| **Reports** | What stakeholder output can I generate safely? | Generate a governed report. |

## Feature map for validation

| Feature area | Current archive signal | Product value | Workshop validation question |
|---|---|---|---|
| **Desktop Studio shell** | Electron app with local Python server, splash, settings, about. | Gives a controlled local workbench experience. | Is local desktop the correct first delivery model, or should web/server mode become primary later? |
| **Inventory / Registry** | Resources, clients, client scope, coverage, library, registry persistence. | Establishes ownership and audit scope. | What is the minimum inventory model: URL list, client/project/resource hierarchy, or full portfolio governance? |
| **Governed audit launch** | Start audit wizard and run lifecycle. | Makes audit setup intentional and repeatable. | What must be captured before an audit is considered governed? |
| **Audit Evidence Hub** | Run history, scores, artifacts, previews, structured findings. | Keeps audit evidence inspectable and reusable. | What evidence must be visible first for trust: score, findings, artifact list, or raw preview? |
| **Expert Review Queue** | Findings review states and candidate-finding framing. | Prevents automation from becoming unverified truth. | What states should be mandatory before findings can move to reports or handoff? |
| **WCAG Mapping Review** | Suggested mapping, clusters, session confirmation. | Helps experts validate compliance framing. | Should WCAG review be its own stage or a mode inside Review findings? |
| **Fix & verify** | Engineering handoff, owner, AC, retest, approval gates. | Converts findings into delivery-ready work. | What is the minimum handoff package engineers need to act confidently? |
| **Traceability** | Chain from resource/evidence/WCAG/test/owner/remediation/verification. | Makes decisions auditable and explainable. | Which trace links are essential for MVP versus advanced governance? |
| **Monitoring** | Drift control, baselines, alerts, resources/components tabs. | Prevents silent regression. | Is monitoring a core release feature or a proof-of-direction feature? |
| **Reports** | Publication console, report types, provenance, gated Markdown export. | Turns reviewed evidence into stakeholder outputs. | Which report is the first must-have: executive risk, consultant findings, engineering handoff, WCAG coverage, regression drift, or portfolio health? |
| **Settings / About / diagnostics** | Engine readiness, data boundaries, local paths, system map. | Builds trust and supportability. | Which details belong in primary UX versus Advanced/Diagnostics only? |

## Recommended product framing for the team

Use this framing in the workshop:

**A11y Studio is not a scanner.** Scanners find problems, but teams still struggle with ownership, evidence, expert validation, engineering handoff, regression control, and reporting.

**A11y Studio is not a generic dashboard.** A dashboard shows status, but it often does not help the team move from risk to verified action.

**A11y Studio is a governed accessibility workflow.** It connects resources, evidence, expert decisions, fixes, monitoring, and publication in one local-first workbench.

## Suggested 90-minute workshop agenda

### 0–10 min — Opening and product intent

Goal: establish the product in one sentence.

Prompt:

> “When this product is successful, what job will users hire it to do?”

Decision to capture:

- Primary product promise.
- Primary user for the first release.

### 10–25 min — Problem story

Walk through the old-world story: scattered scans, unclear ownership, lost evidence, weak handoff, regression risk, hard-to-defend reports.

Prompt:

> “Which pain is most urgent for our users: finding issues, reviewing issues, fixing issues, monitoring regressions, or reporting confidence?”

Decision to capture:

- Top two pains.
- Pain that is explicitly not the first release focus.

### 25–45 min — Journey validation

Review the proposed journey:

```text
Home → Inventory → Start audit → Audit results → Review findings → Fix & verify → Monitor → Reports
```

Prompt:

> “Does this journey match how accessibility work should happen, or are we forcing an internal model onto users?”

Decision to capture:

- Canonical journey labels.
- Whether WCAG Review is a top-level stage or a sub-mode under Review findings.
- Whether Test Plans belongs under Reports, Review, or future roadmap.

### 45–65 min — Feature priority mapping

Use the feature map table. Ask the team to classify each feature:

- **Core MVP** — required for the product to make sense.
- **Support** — needed but not the main story.
- **Proof-of-direction** — show capability, but label honestly.
- **Later** — remove from primary UX for now.

Prompt:

> “What is the smallest end-to-end flow that proves the product value?”

Decision to capture:

- MVP workflow.
- Features to hide, collapse, or clearly mark as sample/roadmap.

### 65–80 min — UX simplification principles

Review the redesign principles:

- one clear location;
- one primary question per workspace;
- one dominant action per page;
- larger readable text;
- technical details moved to Advanced/Sources used;
- no duplicate nav layers;
- sample/live state clearly labeled only where relevant;
- evidence visible, but not as raw file/API noise.

Prompt:

> “What must a first-time user understand in the first 60 seconds?”

Decision to capture:

- First-screen content for Home.
- Terms to ban from primary UI.
- Preferred wording for sample/demo/live states.

### 80–90 min — Decisions and next steps

Close by confirming:

1. Product promise.
2. Primary user.
3. MVP journey.
4. Feature priority map.
5. UX simplification rules.
6. Open questions and owners.

## Opening script

Use this as the first 2–3 minutes of the workshop.

> Today we are aligning on what Forge A11y Studio is, why it matters, and which product features need to be validated first.
>
> The archive already shows a broad product: local desktop shell, inventory, governed audit runs, audit evidence, expert review, WCAG mapping, remediation handoff, traceability, monitoring, and reports. The risk is that the product currently feels more complicated than the problem it solves. Users see too many internal details before they understand the value.
>
> Our goal is to simplify the product story. A11y Studio should not feel like a collection of technical panels. It should feel like a clear control workbench for accessibility work: know what we own, collect evidence, review findings, fix and verify, monitor drift, and publish reports.
>
> The key principle is: automation assists, experts decide, and evidence travels with the decision.
>
> By the end of this workshop, we should agree on the core user, the core journey, which features are MVP versus supporting, and what the redesigned Studio must communicate in the first minute.

## Narrative demo story

Use this story to explain the product value without going into implementation details.

### Scenario: preparing an accessibility review for a customer portal

A product owner is preparing a release of a customer portal. They need to know whether accessibility risk is under control and what engineering must fix before launch.

1. **Home** shows that the customer portal has unresolved accessibility risk and missing recent evidence.
2. **Inventory** confirms that the portal, pricing page, shared header, and checkout journey are owned resources and are in audit scope.
3. **Start audit** lets the team choose the resource and save a governed evidence package.
4. **Audit results** shows what happened: score, evidence package, candidate findings, and downloadable artifacts.
5. **Review findings** lets the accessibility expert confirm what is real, reject false positives, and mark uncertain items for manual testing.
6. **WCAG review** confirms the mapping and severity so the team does not overstate or understate compliance risk.
7. **Fix & verify** turns confirmed findings into engineering-ready work with owner, acceptance criteria, retest steps, and approval.
8. **Monitor** checks whether future builds regress against the baseline.
9. **Reports** creates an executive risk summary or engineering handoff that clearly labels reviewed facts, draft automation, approved guidance, and sample data.

The outcome is not just a list of issues. The outcome is a defensible chain from evidence to decision to action.

## Recommended MVP hypothesis

The strongest MVP should prove this loop:

```text
Inventory → Start audit → Audit results → Review findings → Fix & verify → Report
```

Monitoring and advanced traceability are powerful, but they can be positioned as the next layer unless the team agrees regression control is the main wedge.

Recommended MVP value statement:

> “In one local workspace, an accessibility expert can run an audit, review evidence-backed findings, prepare an engineering handoff, and generate a governed report without losing traceability.”

## What should be simplified in the product experience

The UX should be redesigned around the product story. The current archive and screenshots show issues that should be treated as product blockers, not cosmetic problems.

| Issue | Why it damages value | Product-level fix |
|---|---|---|
| Too many navigation layers | Users cannot tell where they are. | One journey nav, one breadcrumb/location line, contextual tabs only inside selected objects. |
| Technical details in primary UI | Users feel they must understand internals to use the product. | Move route params, API names, filenames, storage, engine names, and paths to Advanced/Sources used. |
| Small muted text for important meaning | Main messages feel like footnotes. | Make page purpose, state, and next action visually dominant. |
| Repeated phrases and sample warnings | Product feels unfinished and noisy. | Say governance/sample status once per workspace or only on affected widgets. |
| Primary actions buried mid-page | Users do not know what to do next. | One dominant action above the fold on every page. |
| Empty states are dead ends | Users cannot recover from missing data. | Empty state = what is missing + why it matters + one primary action + optional sample. |
| Registry/client scope confusion | Ownership and coverage are unclear. | Treat Inventory as the source of truth; make client/resource linking explicit and actionable. |
| Disabled/future features in prime space | Roadmap noise competes with current value. | Move planned items to roadmap/help, not primary workflows. |

## Workshop validation board

Use this table live in the meeting.

| Decision | Options | Team decision |
|---|---|---|
| Primary user | Accessibility consultant / product owner / engineering lead / QA / governance owner |  |
| First value wedge | Evidence audit / expert review / handoff / monitoring / reporting |  |
| MVP journey | Full loop / audit-to-review / review-to-handoff / monitor-first / report-first |  |
| Top nav labels | Home, Inventory, Start audit, Audit results, Review findings, Fix & verify, Monitor, Reports / alternative |  |
| WCAG review placement | Top-level / inside Review findings / inside Reports / advanced only |  |
| Monitoring priority | Core MVP / beta / roadmap |  |
| Reports priority | Executive first / consultant first / engineering first / portfolio first |  |
| Sample data strategy | Global banner / per-widget label / sample mode only / hidden in production |  |
| Technical details | Advanced only / visible to expert users / configurable detail level |  |
| First-screen Home | attention queue / risk score / audit status / inventory gaps / latest result |  |

## Proposed success metrics

These are workshop validation metrics, not claims of current product performance.

| Outcome | Possible measure |
|---|---|
| Users understand the product quickly | New user can explain the product purpose after 60 seconds. |
| Navigation is clear | User can identify current stage and next action on every page. |
| Evidence is trusted | Reviewer can find evidence behind a finding without asking engineering. |
| Handoff is actionable | Engineer can understand what to fix, acceptance criteria, and retest steps. |
| Governance is credible | Report clearly separates reviewed facts, draft automation, approved guidance, and sample data. |
| Regression risk is visible | Team can see what changed since the previous baseline. |

## Recommended closing statement

> The product succeeds when accessibility work stops being a scattered set of scan outputs and becomes a governed workflow. A11y Studio should make the next action obvious, keep evidence attached to every decision, and help teams move from risk to verified remediation with confidence.

