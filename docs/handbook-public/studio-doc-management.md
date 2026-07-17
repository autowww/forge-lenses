# Studio — Doc Management sessions

Governed **Hydration v2** workflow in Lenses Studio under **Publish → Doc management**.

## Routes

| Studio path | Purpose |
|-------------|---------|
| `/studio/doc-management` | Session hub — list sessions, start new |
| `/studio/doc-management/session/:id` | Wizard + workflow console |

## Workflow

1. **Intake** — paste Markdown, zip of `.md` files, URL (HTML stripped to text), or **Hydrate from this post** on a blog article.
2. **Wizard** — pick persona, target surfaces (blog, handbooks, tutorials), optional governed LLM.
3. **Run** — `doc_hydration_agent.py` (route + drafts) then `doc_hydration_worker` (claims + brief).
4. **Review** — inspect pack artifacts; save `reviewer-decision-manifest.json`.
5. **Promote** — dry-run or apply via `promote_session_pack.py` (branch `doc-mgmt/<session-id>` per repo, no auto-push).
6. **Rollback** — `rollback_session_promotion.py` using `promotion/snapshot.json`.

## API

See [HTTP API — doc-management](../lenses/website/http-api-and-routes.md) (`/api/doc-management/*`, SSE `session-events`).

## Feature flag

- Client: `VITE_EXPERIMENTAL_DOC_MANAGEMENT` (default on unless `0` / `false`)
- Server: `LENSES_DOC_MANAGEMENT` (default on unless `0` / `false`)

## Trust boundary

Studio never auto-promotes without a valid reviewer manifest (quality gate G3). Promotion writes only to feature branches until an operator pushes.
