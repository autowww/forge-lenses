export type PipelineStatus = 'stopped' | 'starting' | 'running' | 'stopping' | 'error'

export type PipelineErrorCode =
  | 'CAMERA_BUSY'
  | 'FORMAT_NEGOTIATION_FAILED'
  | 'DEVICE_MISSING'
  | 'PIPELINE_FAILED'
  | 'UNKNOWN'

export type BlurLevel = 'off' | 'light' | 'medium' | 'strong'

export type CameraFormat = {
  fourcc?: string
  description?: string
  sizes?: Array<{ width?: number; height?: number; fps?: number[] }>
}

export type CameraDevice = {
  device_path?: string
  label?: string
  stable_id?: string
  driver?: string
  is_virtual?: boolean
  busy?: boolean
  busy_holders?: Array<{ pid?: number; command?: string }>
  formats?: CameraFormat[]
}

export type ProfileSource = {
  stable_id?: string
  device_path?: string
  label?: string
}

export type ProfileVirtual = {
  device_path?: string
  card_label?: string
}

export type CameraPipelineRuntime = {
  state?: PipelineStatus
  pid?: number | null
  started_at?: string | null
  elapsed_seconds?: number | null
  last_error?: string | null
  error_code?: PipelineErrorCode | null
  error_detail?: string | null
  stderr_tail?: string | null
  source_busy_holder?: Array<{ pid?: number; command?: string }> | null
  input_device_path?: string | null
  output_device_path?: string | null
}

export type CameraProfile = {
  id: string
  name: string
  source?: ProfileSource
  virtual?: ProfileVirtual
  resolution?: { width?: number; height?: number }
  fps?: number
  input_format?: string
  output_format?: string
  mirror?: boolean
  blur_level?: BlurLevel
  runtime?: CameraPipelineRuntime
}

export type BootstrapPayload = {
  ok?: boolean
  ready?: boolean
  module_installed?: boolean
  module_loaded?: boolean
  setup_steps?: string[]
  setup_issue?: string
  setup_issue_message?: string
  privilege_note?: string
  primary_sudo_command?: string
  primary_sudo_action?: string
  privileged_commands?: {
    install?: string
    modprobe?: string
    verify?: string
    persist?: string
  }
}

/** Display path as `video10` (not `videovideo10` from naive `/dev/` strip). */
export function formatDevicePath(path: string | undefined): string {
  const p = (path || '').trim()
  if (!p) return '—'
  if (p.startsWith('/dev/')) return p.slice(5)
  return p
}

/** Prefer MJPEG when advertised; otherwise map the camera's first fourcc. */
export function preferredInputFormat(formats: CameraFormat[] | undefined): string {
  const list = formats || []
  const fourccs = list.map((f) => (f.fourcc || '').toUpperCase())
  if (fourccs.some((f) => f === 'MJPG' || f === 'MJPEG')) return 'MJPEG'
  const first = fourccs[0]
  if (first === 'GREY') return 'GREY'
  if (first === 'YUYV' || first === 'YUY2') return 'YUYV'
  if (first === 'H264') return 'H264'
  return first || 'MJPEG'
}

export function blurLabel(level: BlurLevel | string | undefined): string {
  const v = (level || 'off').toLowerCase()
  if (v === 'off') return 'No blur'
  return `Blur ${v}`
}

export function statusLabel(state: PipelineStatus | string | undefined): string {
  switch ((state || 'stopped').toLowerCase()) {
    case 'running':
      return 'RUNNING'
    case 'starting':
      return 'STARTING'
    case 'stopping':
      return 'STOPPING'
    case 'error':
      return 'ERROR'
    default:
      return 'STOPPED'
  }
}
