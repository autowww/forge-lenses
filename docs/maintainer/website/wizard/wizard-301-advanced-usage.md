# Wizard 301 — Advanced usage

This page goes deeper on **artifact bundles**, **LLM-assisted refinement**, **review and recheck**, **Cursor Launch Pack**, optional **GitHub repo creation**, **feature flags**, and **troubleshooting**.

## Artifact bundles (planning → full stack)

Depending on step **Target & Output Pack**, you can steer generation toward bundles that match your phase:

| Bundle (conceptual) | Typical use |
|---------------------|-------------|
| **Planning** | Roadmaps, milestones, WBS-oriented slices, communication |
| **Engineering** | APIs, modules, test and rollout notes |
| **Execution** | Sparks, charge-oriented tasks, operational checks |
| **Full stack** | Broader slices when scope spans product + infra |

Exact labels in the UI may vary by version; treat bundles as **what gets emphasized** in generated artifacts, not as a promise of automatic repo edits.

## Refine and the LLM loop

Steps like **Understanding** may offer **Refine**: the model reshapes your notes into a clearer brief. **You stay in control**: read the output, edit step notes, and refine again if needed. The same **trust posture** applies as elsewhere in Lenses (typically **loopback** for actions; see server docs if you bind beyond localhost).

**Tips**

- Paste **constraints** explicitly (compliance, regions, “must use X”).
- Keep **non-goals** in step notes so refinement does not re-expand scope.
- If the model drifts, **narrow** the paragraph you send and refine again.

## Review, approve, recheck

**Review & Generate** is where you read generated **Markdown** and structured slices. Treat this as a **gate**: if something is wrong, fix upstream notes and regenerate rather than editing only the preview.

**Recheck / Repair** runs consistency checks (and optional **preview without save** flows depending on build). Use **Refresh recheck** when you have persisted a new summary and want the session updated.

## Cursor Launch Pack (Experimental Build)

The last step packages **context and files** so you can continue in **Cursor** (or another editor) with less copy-paste. You may see:

- **Preview** of what will ship in the pack
- **Download** (sometimes large zips are **staged** with a time-to-live)
- **Workspace export** paths when your policy allows writing beside your workspace root

Always read **warnings** from the pack step—strict approval modes may block export until slices are locked.

## GitHub repository creation (optional)

Some setups allow **creating a new GitHub repository** after explicit confirmation. **Personal access tokens** are read from the server environment (**`GITHUB_TOKEN`** / **`LENSES_GITHUB_TOKEN`**)—they are **not** stored in session JSON. If your org forbids token use on this host, skip repo creation and clone manually.

## Feature flags (reference)

| Variable | Role |
|----------|------|
| `LENSES_EXPERIMENTAL_BLUEPRINTS_WIZARD` | Server: `0` / `false` / `off` disables most wizard APIs (probe endpoint may still report state). |
| `VITE_EXPERIMENTAL_BLUEPRINTS_WIZARD` | Client build: `false` / `0` omits wizard routes and sidebar entry. |

Defaults are **on** in many dev builds; production packaging may differ.

## Troubleshooting

| Symptom | What to try |
|---------|-------------|
| **Wizard routes missing** | Rebuild Studio with wizard flag on; confirm you are on **`/studio/…`**, not Classic-only. |
| **“Local draft only”** | Ensure Lenses is running; click **Retry**; check server wizard flag and logs. |
| **LLM actions fail** | Confirm loopback / allow-actions policy; no prompts stored in telemetry logs by design—check server stderr. |
| **Save / PUT errors** | Disk space, permissions on **`.lenses-local/`**, or static “museum” builds that cannot persist—use a live server. |
| **Concurrent tabs** | Last write wins—use one tab per session for critical work. |

## Next

- [Wizard guides index](index.md)
- [User guide home](../home.md)
