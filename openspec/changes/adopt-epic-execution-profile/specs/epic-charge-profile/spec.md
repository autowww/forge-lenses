## Purpose

Under the Epic execution profile, forge-lenses uses Charge as a view on **committed Epics** (not Forge Sparks). This capability binds observable acceptance for the daily Charge artifact and its link to profile canon and OpenSpec changes.

## ADDED Requirements

### Requirement: Active Epics on Charge

The repository's daily Charge **under the Epic execution profile** SHALL include an **Active Epics** table where each Charged row lists the WBS Epic id, the linked OpenSpec change identifier, and a status visible to maintainers.

#### Scenario: Charge lists Epics not Sparks

- **WHEN** a maintainer opens today's Charge document for this repository
- **THEN** they see an **Active Epics** table (not an **Active Sparks** table) and the header states the repo runs under the Epic execution profile

#### Scenario: Charged Epic traces to OpenSpec

- **WHEN** an Epic is listed on today's Charge
- **THEN** the row includes the WBS Epic id (e.g. `M1E3`), the OpenSpec change slug, and a status value

#### Scenario: Profile canon is reachable from Charge

- **WHEN** a reader needs context on Epic vs Spark Charge grain
- **THEN** the Charge document links to the Epic execution profile canon so dual-profile behavior is explicit
