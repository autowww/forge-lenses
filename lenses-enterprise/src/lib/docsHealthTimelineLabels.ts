/** Human-readable labels for Docs Health session timeline event ``type`` values. */

const KIND_LABELS: Record<string, string> = {
  summary: 'Summary',
  question: 'Question',
  file_inquiry: 'File inquiry',
  plan: 'Plan',
  diff: 'Diff preview',
  file_change: 'File change',
  command: 'Command',
  command_result: 'Command result',
  verification: 'Verification',
  work_item: 'Work item',
  kpi_update: 'KPI update',
  token_stats: 'Token & model',
  user_reply: 'Your reply',
}

export function docsHealthEventKindLabel(type: string | undefined): string {
  const t = String(type || '').trim().toLowerCase()
  return KIND_LABELS[t] || (t ? t.replace(/_/g, ' ') : 'Event')
}
