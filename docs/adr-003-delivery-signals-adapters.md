# ADR 003: Delivery signals — local fixtures and provider adapters

## Status

Accepted (initial slice: local JSON + scan merge; remote adapters stubbed).

## Context

Forge Lenses / Studio already excels at workspace scan, planning, and markdown evidence. Gaps for **SDLC orchestration** include CI/CD visibility, PR/trace links, environments, and releases without turning the product into a generic content portal.

Requirements:

- **Local-first**: signals must augment the existing scan, not replace it.
- **Feature flag**: gate risky behavior; default-on is acceptable when there is **no outbound network** (fixtures only).
- **Adapters**: GitHub Actions, GitLab, Jenkins, Argo, Datadog, Sentry, etc. must plug in **without rewriting** the domain payload.
- **Disconnected / read-only**: APIs return **200** with explanatory **`hints`** when disabled or empty; static museum ships JSON snapshots.

## Decision

1. **Contract** — `GET /api/delivery/overview` returns **`schema_version`: 1** with **`repos[]`** aligned to **`scan_workspace` children**, each row carrying **`data_sources`** (`workspace_scan`, `local_fixture`, future `github_actions`, …).
2. **Local fixture file** — **`<workspace>/.lenses-local/delivery-signals.json`**: optional map **`repos[child_name]`** with **`ci_provider`**, **`workflows`**, **`trace_links`**, **`environments`**, **`releases`** (lists of small objects; URLs are opaque strings).
3. **Feature flag** — **`LENSES_EXPERIMENTAL_DELIVERY_SIGNALS`**: explicit **`0` / false / no / off** disables overlays (API returns **`feature_enabled`: false** and **`repos`: []** with hints). Unset defaults to **on** (same pattern as Blueprints Wizard).
4. **Demo seed** — **`LENSES_DELIVERY_SIGNALS_SEED_DEMO=1`** merges **`lenses/fixtures/delivery-signals.demo.json`** when no user file exists (docs/demos only).
5. **Adapter port** — **`lenses.delivery_signals.protocol.DeliverySignalsProvider`** defines **`augment_repo_row(...)`**; **`providers/null_remote.py`** is the no-op implementation until credentials and rate limits are specified per vendor.
6. **UI** — Studio **Plan → Today** adds **Pipeline and traceability** (no new top-level route). Telemetry tags: **`delivery_signals_*`** via existing Studio UX buffer.

## Consequences

- **No migrations**: JSON documents only; no SQLite schema change in this ADR.
- **Next steps**: Implement one remote provider (e.g. GitHub Actions) behind **`LENSES_DELIVERY_REMOTE_ADAPTERS`** (or per-provider flags), call provider from `build_delivery_overview_payload` after local merge, respect RBAC and PAT storage rules already used by **`/api/auth/github`**.

## Related

- **`lenses/delivery_signals/`** — aggregate, feature flag, local store, protocol.
- **`lenses/website/http-api-and-routes.md`** — HTTP contract.
- **`lenses/fixtures/delivery-signals.demo.json`** — sample fixture.
