import { describe, expect, it } from 'vitest'
import {
  applyBalancedPreset,
  buildEditorCapabilityOptions,
  fourccToInputFormat,
  matchQualityPreset,
  pickSourceDevice,
} from './virtualCameraEditorOptions'
import type { CameraDevice } from './virtualCameraTypes'

const SAMPLE_FORMATS = [
  {
    fourcc: 'MJPG',
    sizes: [
      { width: 1920, height: 1080, fps: [30, 15] },
      { width: 1280, height: 720, fps: [30, 15] },
      { width: 640, height: 360, fps: [30, 15] },
    ],
  },
  {
    fourcc: 'YUYV',
    sizes: [{ width: 640, height: 480, fps: [30, 15] }],
  },
]

describe('virtualCameraEditorOptions', () => {
  it('maps fourcc to pipeline input format', () => {
    expect(fourccToInputFormat('MJPG')).toBe('MJPEG')
    expect(fourccToInputFormat('GREY')).toBe('GREY')
  })

  it('prefers MJPG device path for the same stable id', () => {
    const cameras: CameraDevice[] = [
      {
        stable_id: 'usb:1',
        device_path: '/dev/video2',
        formats: [{ fourcc: 'GREY', sizes: [{ width: 400, height: 360, fps: [15] }] }],
      },
      {
        stable_id: 'usb:1',
        device_path: '/dev/video0',
        formats: [{ fourcc: 'MJPG', sizes: [{ width: 1280, height: 720, fps: [30] }] }],
      },
    ]
    expect(pickSourceDevice(cameras, 'usb:1')?.device_path).toBe('/dev/video0')
  })

  it('builds graded quality presets', () => {
    const options = buildEditorCapabilityOptions(SAMPLE_FORMATS, 'MJPEG')
    expect(options.presets.map((p) => p.id)).toEqual([
      'original',
      'ultra',
      'high',
      'balanced',
      'smooth',
      'low_bandwidth',
      'avd_teams',
      'vdi_ultra_low',
      'vdi_minimal',
    ])
    const balanced = options.presets.find((p) => p.id === 'balanced')
    expect(balanced?.width).toBe(1280)
    expect(balanced?.height).toBe(720)
    expect(balanced?.fps).toBe(30)
  })

  it('builds vdi ultra-low and minimal presets', () => {
    const options = buildEditorCapabilityOptions(SAMPLE_FORMATS, 'MJPEG')
    const ultraLow = options.presets.find((p) => p.id === 'vdi_ultra_low')
    const minimal = options.presets.find((p) => p.id === 'vdi_minimal')
    expect(ultraLow?.width).toBe(320)
    expect(ultraLow?.height).toBe(160)
    expect(ultraLow?.fps).toBe(15)
    expect(minimal?.width).toBe(160)
    expect(minimal?.height).toBe(120)
    expect(minimal?.fps).toBe(15)
    expect(options.resolutions.some((r) => r.key === '320x160')).toBe(true)
    expect(options.resolutions.some((r) => r.key === '96x72')).toBe(true)
  })

  it('matches custom when settings diverge from presets', () => {
    const options = buildEditorCapabilityOptions(SAMPLE_FORMATS, 'MJPEG')
    const id = matchQualityPreset(options.presets, 320, 240, 15, 'MJPEG')
    expect(id).toBe('custom')
  })

  it('applyBalancedPreset returns sensible defaults', () => {
    const applied = applyBalancedPreset(SAMPLE_FORMATS)
    expect(applied.width).toBe(1280)
    expect(applied.quality_preset).toBe('balanced')
  })
})
