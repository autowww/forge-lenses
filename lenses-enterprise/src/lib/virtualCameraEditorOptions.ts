import type { CameraDevice, CameraFormat } from './virtualCameraTypes'
import { preferredInputFormat } from './virtualCameraTypes'

export type QualityPresetId =
  | 'original'
  | 'ultra'
  | 'high'
  | 'balanced'
  | 'smooth'
  | 'low_bandwidth'
  | 'avd_teams'
  | 'vdi_ultra_low'
  | 'vdi_minimal'
  | 'custom'

/** Presets that set MJPEG/NV12 output for RDP camera redirect. */
export type VdiQualityPresetId = 'avd_teams' | 'vdi_ultra_low' | 'vdi_minimal'

export const VDI_QUALITY_PRESET_IDS: readonly VdiQualityPresetId[] = [
  'avd_teams',
  'vdi_ultra_low',
  'vdi_minimal',
]

export function isVdiQualityPresetId(id: string): id is VdiQualityPresetId {
  return (VDI_QUALITY_PRESET_IDS as readonly string[]).includes(id)
}

export type QualityPreset = {
  id: QualityPresetId
  label: string
  hint: string
  width: number
  height: number
  fps: number
  input_format: string
}

export type ResolutionOption = {
  key: string
  width: number
  height: number
  label: string
  native: boolean
  fps: number[]
}

export type EditorCapabilityOptions = {
  inputFormats: string[]
  outputFormats: string[]
  resolutions: ResolutionOption[]
  fpsOptions: number[]
  presets: QualityPreset[]
  maxNative: { width: number; height: number; fps: number; input_format: string }
}

const OUTPUT_FORMAT_ORDER = ['MJPEG', 'NV12', 'YUYV', 'UYVY', 'RGB', 'BGR', 'GREY'] as const

const DEFAULT_OUTPUT_FORMATS = ['YUYV', 'UYVY', 'NV12', 'MJPEG', 'RGB', 'BGR', 'GREY'] as const

const STANDARD_RESOLUTIONS: Array<{ width: number; height: number }> = [
  { width: 1920, height: 1080 },
  { width: 1280, height: 720 },
  { width: 960, height: 540 },
  { width: 800, height: 600 },
  { width: 640, height: 480 },
  { width: 640, height: 360 },
  { width: 320, height: 240 },
  { width: 320, height: 180 },
  { width: 320, height: 160 },
  { width: 256, height: 144 },
  { width: 176, height: 144 },
  { width: 160, height: 120 },
  { width: 128, height: 96 },
  { width: 96, height: 72 },
]

const PRESET_SPECS: Array<{
  id: QualityPresetId
  label: string
  hint: string
  targetArea: number
  fps: number
}> = [
  {
    id: 'original',
    label: 'Original (camera native)',
    hint: 'Maximum resolution and frame rate the source advertises.',
    targetArea: Number.POSITIVE_INFINITY,
    fps: -1,
  },
  {
    id: 'ultra',
    label: 'Ultra quality',
    hint: 'Highest resolution with a steady 15 fps for crisp still-like video.',
    targetArea: Number.POSITIVE_INFINITY,
    fps: 15,
  },
  {
    id: 'high',
    label: 'High quality',
    hint: '1080p-class resolution at 15 fps — good for presentations and VDI.',
    targetArea: 1920 * 1080,
    fps: 15,
  },
  {
    id: 'balanced',
    label: 'Balanced',
    hint: '720p-class at 30 fps — default for meetings and browsers.',
    targetArea: 1280 * 720,
    fps: 30,
  },
  {
    id: 'smooth',
    label: 'Smooth motion',
    hint: 'VGA-class resolution at 30 fps for responsive motion.',
    targetArea: 640 * 480,
    fps: 30,
  },
  {
    id: 'low_bandwidth',
    label: 'Low bandwidth',
    hint: '360p at 15 fps for constrained VDI or uplinks.',
    targetArea: 640 * 360,
    fps: 15,
  },
  {
    id: 'avd_teams',
    label: 'AVD Teams (Cloud PC)',
    hint: '640×360 at 15 fps for Azure Windows Cloud VDI + Teams on RDP camera redirect.',
    targetArea: 640 * 360,
    fps: 15,
  },
  {
    id: 'vdi_ultra_low',
    label: 'VDI ultra-low (non-optimized)',
    hint: '320×160 at 15 fps — lower bandwidth when Teams is not VDI-optimized.',
    targetArea: 320 * 160,
    fps: 15,
  },
  {
    id: 'vdi_minimal',
    label: 'VDI minimal',
    hint: '160×120 at 10 fps — smallest practical frame for blocky RDP redirect paths.',
    targetArea: 160 * 120,
    fps: 10,
  },
]

export function fourccToInputFormat(fourcc: string | undefined): string {
  const key = (fourcc || '').trim().toUpperCase()
  if (key === 'MJPG' || key === 'MJPEG') return 'MJPEG'
  if (key === 'YUY2' || key === 'YUYV') return 'YUYV'
  if (key === 'GREY' || key === 'GRAY8') return 'GREY'
  if (key === 'H264') return 'H264'
  return key || 'MJPEG'
}

export function inputFormatToFourcc(inputFormat: string): string {
  const key = (inputFormat || '').trim().toUpperCase()
  if (key === 'MJPEG' || key === 'MJPG') return 'MJPG'
  if (key === 'YUYV') return 'YUY2'
  if (key === 'GREY' || key === 'GRAY8') return 'GREY'
  return key
}

export function outputLabelMatchesFourcc(label: string, fourcc: string): boolean {
  const f = (fourcc || '').trim().toUpperCase()
  const norm = (label || '').trim().toUpperCase()
  if (norm === 'MJPEG' && (f === 'MJPG' || f === 'MJPEG')) return true
  if (norm === 'YUYV' && (f === 'YUY2' || f === 'YUYV')) return true
  if (norm === 'GREY' && (f === 'GREY' || f === 'GRAY8' || f === 'GRAY')) return true
  if (norm === 'NV12' && f === 'NV12') return true
  return norm === f
}

export function buildOutputFormatOptions(virtualFormats: CameraFormat[] | undefined): string[] {
  const fourccs = (virtualFormats ?? [])
    .map((fmt) => (fmt.fourcc || '').trim().toUpperCase())
    .filter(Boolean)
  if (!fourccs.length) return [...DEFAULT_OUTPUT_FORMATS]
  const found: string[] = []
  for (const label of OUTPUT_FORMAT_ORDER) {
    if (fourccs.some((f) => outputLabelMatchesFourcc(label, f))) {
      found.push(label)
    }
  }
  return found.length ? found : ['YUYV']
}

export function pickPreferredVdiOutputFormat(virtualFormats: CameraFormat[] | undefined): string {
  const opts = buildOutputFormatOptions(virtualFormats)
  if (opts.includes('MJPEG')) return 'MJPEG'
  if (opts.includes('NV12')) return 'NV12'
  return opts[0] ?? 'YUYV'
}

export function pickSourceDevice(cameras: CameraDevice[], stableId: string): CameraDevice | undefined {
  const matches = cameras.filter((c) => c.stable_id === stableId)
  if (!matches.length) return undefined
  const mjpg = matches.find((c) =>
    (c.formats ?? []).some((f) => (f.fourcc || '').toUpperCase() === 'MJPG'),
  )
  return mjpg ?? matches[0]
}

function uniqueSorted(nums: number[]): number[] {
  return [...new Set(nums.filter((n) => Number.isFinite(n) && n > 0))].sort((a, b) => a - b)
}

function uniqueSortedStrings(items: string[]): string[] {
  return [...new Set(items.map((s) => s.trim()).filter(Boolean))].sort()
}

function resolutionKey(width: number, height: number): string {
  return `${width}x${height}`
}

function resolutionLabel(width: number, height: number, native: boolean): string {
  const tag = native ? 'native' : 'scaled'
  return `${width}×${height} (${tag})`
}

function collectNativeResolutions(formats: CameraFormat[] | undefined): ResolutionOption[] {
  const map = new Map<string, ResolutionOption>()
  for (const fmt of formats ?? []) {
    const inputFormat = fourccToInputFormat(fmt.fourcc)
    for (const size of fmt.sizes ?? []) {
      const width = Number(size.width ?? 0)
      const height = Number(size.height ?? 0)
      if (width <= 0 || height <= 0) continue
      const key = resolutionKey(width, height)
      const fps = uniqueSorted((size.fps ?? []).map((f) => Math.round(Number(f))))
      const existing = map.get(key)
      if (existing) {
        existing.fps = uniqueSorted([...existing.fps, ...fps])
        existing.native = true
      } else {
        map.set(key, {
          key,
          width,
          height,
          label: resolutionLabel(width, height, true),
          native: true,
          fps,
        })
      }
      void inputFormat
    }
  }
  return [...map.values()].sort((a, b) => b.width * b.height - a.width * a.height)
}

function maxNativeCapability(formats: CameraFormat[] | undefined): {
  width: number
  height: number
  fps: number
  input_format: string
} {
  const input_format = preferredInputFormat(formats)
  const fourcc = inputFormatToFourcc(input_format)
  let bestArea = 0
  let width = 640
  let height = 360
  let fps = 15
  for (const fmt of formats ?? []) {
    if ((fmt.fourcc || '').toUpperCase() !== fourcc && fourcc !== (fmt.fourcc || '').toUpperCase()) {
      if (fourcc === 'MJPG' && (fmt.fourcc || '').toUpperCase() !== 'MJPG') continue
    }
    for (const size of fmt.sizes ?? []) {
      const w = Number(size.width ?? 0)
      const h = Number(size.height ?? 0)
      const area = w * h
      if (area > bestArea) {
        bestArea = area
        width = w
        height = h
        const fpsList = (size.fps ?? []).map((f) => Math.round(Number(f))).filter((n) => n > 0)
        fps = fpsList.length ? Math.max(...fpsList) : 15
      }
    }
  }
  return { width, height, fps, input_format }
}

function buildResolutionOptions(
  formats: CameraFormat[] | undefined,
  inputFormat: string,
): ResolutionOption[] {
  const native = collectNativeResolutions(formats)
  const max = maxNativeCapability(formats)
  const maxArea = max.width * max.height
  const map = new Map<string, ResolutionOption>()
  for (const item of native) {
    map.set(item.key, { ...item })
  }
  const fourcc = inputFormatToFourcc(inputFormat)
  const fmt = (formats ?? []).find((f) => (f.fourcc || '').toUpperCase() === fourcc)
  const fmtFps = uniqueSorted(
    (fmt?.sizes ?? []).flatMap((s) => (s.fps ?? []).map((f) => Math.round(Number(f)))),
  )
  for (const std of STANDARD_RESOLUTIONS) {
    if (std.width * std.height > maxArea) continue
    const key = resolutionKey(std.width, std.height)
    if (!map.has(key)) {
      map.set(key, {
        key,
        width: std.width,
        height: std.height,
        label: resolutionLabel(std.width, std.height, false),
        native: false,
        fps: fmtFps.length ? fmtFps : [15, 30],
      })
    }
  }
  return [...map.values()].sort((a, b) => b.width * b.height - a.width * a.height)
}

function fpsForResolution(
  resolutions: ResolutionOption[],
  width: number,
  height: number,
  inputFormat: string,
  formats: CameraFormat[] | undefined,
): number[] {
  const key = resolutionKey(width, height)
  const match = resolutions.find((r) => r.key === key)
  if (match?.fps.length) return match.fps
  const fourcc = inputFormatToFourcc(inputFormat)
  const fmt = (formats ?? []).find((f) => (f.fourcc || '').toUpperCase() === fourcc)
  const fromFmt = uniqueSorted(
    (fmt?.sizes ?? []).flatMap((s) => (s.fps ?? []).map((f) => Math.round(Number(f)))),
  )
  if (fromFmt.length) return fromFmt
  return [15, 24, 30]
}

function closestFps(options: number[], target: number): number {
  if (!options.length) return target > 0 ? target : 15
  if (target < 0) return Math.max(...options)
  return options.reduce((best, cur) =>
    Math.abs(cur - target) < Math.abs(best - target) ? cur : best,
  )
}

function pickResolutionForArea(resolutions: ResolutionOption[], targetArea: number): ResolutionOption {
  const sorted = [...resolutions].sort((a, b) => b.width * b.height - a.width * a.height)
  if (!sorted.length) {
    return { key: '640x360', width: 640, height: 360, label: '640×360', native: false, fps: [15] }
  }
  if (!Number.isFinite(targetArea)) return sorted[0]
  let best = sorted[sorted.length - 1]
  let bestDelta = Number.POSITIVE_INFINITY
  for (const res of sorted) {
    const area = res.width * res.height
    if (area > targetArea) continue
    const delta = targetArea - area
    if (delta < bestDelta) {
      bestDelta = delta
      best = res
    }
  }
  return best
}

export function buildQualityPresets(
  formats: CameraFormat[] | undefined,
  resolutions: ResolutionOption[],
  inputFormat: string,
): QualityPreset[] {
  const maxNative = maxNativeCapability(formats)
  const fpsPool = fpsForResolution(resolutions, maxNative.width, maxNative.height, inputFormat, formats)

  return PRESET_SPECS.map((spec) => {
    if (spec.id === 'original') {
      return {
        id: spec.id,
        label: spec.label,
        hint: spec.hint,
        width: maxNative.width,
        height: maxNative.height,
        fps: closestFps(fpsPool, -1),
        input_format: maxNative.input_format,
      }
    }
    const res =
      spec.id === 'ultra'
        ? pickResolutionForArea(resolutions, Number.POSITIVE_INFINITY)
        : pickResolutionForArea(resolutions, spec.targetArea)
    const fpsChoices = fpsForResolution(resolutions, res.width, res.height, inputFormat, formats)
    return {
      id: spec.id,
      label: spec.label,
      hint: spec.hint,
      width: res.width,
      height: res.height,
      fps: closestFps(fpsChoices, spec.fps),
      input_format: inputFormat,
    }
  })
}

export function buildEditorCapabilityOptions(
  formats: CameraFormat[] | undefined,
  inputFormat: string,
  virtualFormats?: CameraFormat[] | undefined,
): EditorCapabilityOptions {
  const inputFormats = uniqueSortedStrings(
    (formats ?? []).map((f) => fourccToInputFormat(f.fourcc)).filter(Boolean),
  )
  if (!inputFormats.length) inputFormats.push('MJPEG', 'YUYV')

  const normalizedInput = inputFormats.includes(inputFormat)
    ? inputFormat
    : preferredInputFormat(formats)

  const resolutions = buildResolutionOptions(formats, normalizedInput)
  const maxNative = maxNativeCapability(formats)
  const presets = buildQualityPresets(formats, resolutions, normalizedInput)

  const defaultRes = resolutions[0] ?? {
    key: '640x360',
    width: 640,
    height: 360,
    label: '640×360',
    native: false,
    fps: [15],
  }

  return {
    inputFormats,
    outputFormats: buildOutputFormatOptions(virtualFormats),
    resolutions,
    fpsOptions: fpsForResolution(
      resolutions,
      defaultRes.width,
      defaultRes.height,
      normalizedInput,
      formats,
    ),
    presets,
    maxNative,
  }
}

export function fpsOptionsForEditor(
  formats: CameraFormat[] | undefined,
  resolutions: ResolutionOption[],
  width: number,
  height: number,
  inputFormat: string,
): number[] {
  return fpsForResolution(resolutions, width, height, inputFormat, formats)
}

export function matchQualityPreset(
  presets: QualityPreset[],
  width: number,
  height: number,
  fps: number,
  inputFormat: string,
): QualityPresetId {
  for (const preset of presets) {
    if (
      preset.width === width &&
      preset.height === height &&
      preset.fps === fps &&
      preset.input_format === inputFormat
    ) {
      return preset.id
    }
  }
  return 'custom'
}

export function applyQualityPreset(preset: QualityPreset): {
  width: number
  height: number
  fps: number
  input_format: string
  quality_preset: QualityPresetId
} {
  return {
    width: preset.width,
    height: preset.height,
    fps: preset.fps,
    input_format: preset.input_format,
    quality_preset: preset.id,
  }
}

export function applyBalancedPreset(formats: CameraFormat[] | undefined): {
  width: number
  height: number
  fps: number
  input_format: string
  quality_preset: QualityPresetId
} {
  const input_format = preferredInputFormat(formats)
  const options = buildEditorCapabilityOptions(formats, input_format)
  const balanced = options.presets.find((p) => p.id === 'balanced') ?? options.presets[0]
  return applyQualityPreset(balanced)
}

export function applyVdiQualityPreset(
  presetId: VdiQualityPresetId,
  sourceFormats: CameraFormat[] | undefined,
  virtualFormats: CameraFormat[] | undefined,
): {
  width: number
  height: number
  fps: number
  input_format: string
  output_format: string
  quality_preset: QualityPresetId
} {
  const input_format = preferredInputFormat(sourceFormats)
  const options = buildEditorCapabilityOptions(sourceFormats, input_format, virtualFormats)
  const preset =
    options.presets.find((p) => p.id === presetId) ??
    options.presets.find((p) => p.id === 'avd_teams') ??
    options.presets.find((p) => p.id === 'low_bandwidth') ??
    options.presets[0]
  const base = applyQualityPreset(preset)
  return {
    ...base,
    output_format: pickPreferredVdiOutputFormat(virtualFormats),
  }
}

export function applyAvdTeamsPreset(
  sourceFormats: CameraFormat[] | undefined,
  virtualFormats: CameraFormat[] | undefined,
): {
  width: number
  height: number
  fps: number
  input_format: string
  output_format: string
  quality_preset: QualityPresetId
} {
  return applyVdiQualityPreset('avd_teams', sourceFormats, virtualFormats)
}
