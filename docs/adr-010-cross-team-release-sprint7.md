# ADR 010: Cross-team dependency and change orchestration (Sprint 7)

## Status

Accepted (local-first fixture merged with live CI/CD, quality, and DevSecOps payloads).

## Context

Release managers, program managers, and cross-team leads needed a **single operational view**: shipping scope, blockers, dependencies across initiatives and environments, change records, lightweight CAB decisions, rollback paths, and meeting-ready artifacts — without treating boards as static templates only.

## Decision

1. **Package** — **`lenses/cross_team_release/`**: **`feature_flag`** (`LENSES_EXPERIMENTAL_CROSS_TEAM_RELEASE`, default on), **`local_store`** (`.lenses-local/cross-team-release.json` + **`lenses/fixtures/cross-team-release.demo.json`** via **`LENSES_CROSS_TEAM_RELEASE_SEED_DEMO=1`**), **`board.build_dependency_board`**, **`calendar.build_release_calendar`**, **`packet.build_go_no_go_packet`**, **`artifacts.build_communication_artifacts`**, **`aggregate.build_cross_team_release_overview`** (pulls **`build_cicd_control_tower_payload`**, and when flags allow **`build_quality_overview_payload`** / **`build_devsecops_overview_payload`**).
2. **Models in fixture** — **`dependency_nodes`** / **`dependency_edges`** (initiative, team, repo, release, environment), **`milestones`**, **`readiness_views`**, **`change_requests`** (scope, risk, approvers, implementation window, rollback notes), **`cab_sessions`** (decisions, attendees).
3. **API** — **`GET /api/cross-team-release/enabled`**, **`GET /api/cross-team-release/overview`**.
4. **Studio** — **Plan → Today**: **`ReleaseManagerCard`** after the CI/CD control tower; copyable go/no-go Markdown and communication drafts.

## Consequences

- **Go/no-go packet** reflects **live** blocked promotions, rollback targets, and quality/security gate lines when those subsystems have fixtures; otherwise sections degrade gracefully with hints.
- **Dependency board** gains **workspace scan** repo nodes so multi-repo workspaces show up on the same graph as initiatives and releases.

## Related

- **`lenses/website/http-api-and-routes.md`**
- **`tests/test_cross_team_release.py`**
