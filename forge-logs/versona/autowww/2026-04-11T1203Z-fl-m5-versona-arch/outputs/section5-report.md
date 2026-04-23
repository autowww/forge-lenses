# Software Architecture Versona — §5 report

**Work item:** M5E2S2 (unified evidence), M5E3S1 (inbox/notifications), M5E5S1 (connectors) — post-BA clarity  
**Phase:** Specify / Design (A–C)  
**Review depth:** High  

## Concerns

| # | Concern | Severity | Recommendation |
|---|---------|----------|----------------|
| 1 | Unified evidence index implies consistency, indexing cost, and privacy across local + optional remote roots. | significant | Choose bounded context: read-only index vs mutable registry; document in ADR before build. |
| 2 | Notifications without delivery guarantees create false security for approvals. | significant | Start event-log + in-app feed; outbound email/Slack as optional channel with explicit non-guarantee. |
| 3 | Connector lineage conflicts with file-first SoR — merge strategy undefined. | significant | Define conflict policy (last-write-wins vs manual resolution) per connector class. |

## Evidence requests

- Quality attribute priorities (2): e.g. privacy > availability for local-first.
- Retention and PII boundaries for any notification store.

## Recommendation

**Bank** on implementation until BA §5 conditions for baseline/evidence are met; then **Proceed with conditions** — spike index + ADR for evidence boundary before M5E3S1 build.
