# Project Management Versona — §5 report

**Work item:** M2 — Monitoring and portfolio signals (M2E1–M2E3), dependency on T5 honesty  
**Phase:** Specify / planning (B)  
**Review depth:** High  

## Concerns

| # | Concern | Severity | Recommendation |
|---|---------|----------|----------------|
| 1 | Delivery KPIs (slip, throughput) are undefined while charts are broken — metrics may measure noise. | significant | Gate **M2E1S1** on T5 chart/API truth or explicit exclusion list (“no metric until source X is reliable”). |
| 2 | Portfolio/attention strip without capacity assumptions over-promises. | minor | Timebox M2E2S1 spike; define “attention” as file-derived first. |
| 3 | Parallel T5 + M2 risks thrash the same API surfaces. | minor | Sequence Sparks: stabilize read APIs, then add snapshots (M2E3). |

## Evidence requests

- Which milestones and Charge fields are authoritative for “slip” in a file-first world.
- Maintainer capacity (hours/week) for M2 vs T5 this quarter.

## Recommendation

**Proceed with conditions** — start M2 planning only with a written source-of-truth map and T5 exit criteria for chart endpoints.
