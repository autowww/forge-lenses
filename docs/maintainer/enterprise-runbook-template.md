# Enterprise runbook template (maintainer-facing)

Audience: **maintainer**. Keep this Markdown under **`docs/maintainer/`**; link from public enterprise chapters via HTTPS GitHub paths when excerpts are needed externally.

Suggested sections:

| Section | Content |
|---------|---------|
| Roles & paging | Incident commander, infra DRI, Wizard maintainer rotation |
| Scope | Regions, subnets, SSO tenants, repos allowed to mount |
| Preconditions | Certificates, JWKS rotations, KMS policies |
| Detect | Telemetry queries, Grafana/Fleet panels, alerting hooks |
| Mitigate | Rollback playbook, draining sessions, patching |
| Recover | Bringing automation back online safely |
| Communicate | Stakeholders + SLA notes |

Embed JSON payloads only when sanitized—reference schema fixtures under **`docs/schemas/`** + **`docs/examples/`**.
