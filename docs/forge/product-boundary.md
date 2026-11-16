# Lenses Product Boundary

## Owns

- local control plane
- workspace state
- ForgeRun display
- approvals
- evidence review
- workcell activity views

## Does not own

- LLM reasoning
- Docker execution
- canonical Blueprints policy
- agent memory

## Consumes

- `forge_run.v1`
- `evidence_packet.v1`
- `lcdl_trace_summary.v1`
- `fleet_job_summary.v1`
- `agent_run.v1`

## Emits

- `approval_request.v1`
- `agent_run.v1`
- `evidence_packet.v1`
- `forge_run.v1`
