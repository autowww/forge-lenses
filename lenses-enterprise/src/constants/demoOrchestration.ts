/** Demo graph root: rate-limit story (see `lenses/fixtures/orchestration-graph.demo.json`). */
export const DEMO_ORCHESTRATION_STORY_ID = 'ogs:demo:story:rate-limit-auth'

/** Bridge B1 demo chain: Ore → Ingot → story → … → release (same fixture). */
export const DEMO_BRIDGE_DEMAND_ID = 'ogs:demo:demand:ore-auth-throttle'

/** Demo scenarios for portfolio comparison (same fixture). */
export const DEMO_SCENARIO_BASELINE_ID = 'ogs:demo:scenario:baseline'
export const DEMO_SCENARIO_STRETCH_ID = 'ogs:demo:scenario:stretch'

/** When workspace child name matches, trace can start at the demo repo entity. */
export function demoRepoEntityId(workspaceChildName: string): string {
  const slug = workspaceChildName.trim().toLowerCase().replace(/[^a-z0-9_-]+/g, '-')
  return `ogs:demo:repo:${slug}`
}
