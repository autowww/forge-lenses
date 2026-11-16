import { useCallback, useEffect, useMemo, useState } from 'react'
import { apiGetJson } from '../api/http'
import { TechnicalDetails } from '../components/page'
import {
  applyVdiQualityPreset,
  pickPreferredVdiOutputFormat,
  type QualityPresetId,
  type VdiQualityPresetId,
} from '../lib/virtualCameraEditorOptions'
import {
  avdDiagnosticSummary,
  parseAvdTeamsDiagnostic,
  type ParsedAvdDiagnostic,
} from '../lib/avdTeamsDiagnostic'
import type { CameraDevice, CameraFormat } from '../lib/virtualCameraTypes'

type VdiReadinessPayload = {
  ok?: boolean
  linux_primary_note?: string
  teams_optimization_note?: string
  recommended_preset_id?: string
  recommended_output_format?: string
  rdp_property_lines?: string[]
  links?: { teams_on_avd?: string; rdp_properties?: string }
  virtual_devices?: Array<{
    device_path?: string
    label?: string
    output_format_options?: string[]
    vdi_friendly?: { mjpeg?: boolean; nv12?: boolean; yuyv?: boolean }
  }>
  running_profiles?: Array<{
    id?: string
    name?: string
    output_format?: string
    resolution?: { width?: number; height?: number }
    fps?: number
  }>
}

type VdiTeamsReadinessCardProps = {
  sourceFormats: CameraFormat[] | undefined
  virtualCameras: CameraDevice[]
  selectedVirtualPath: string
  onApplyAvdPreset: (patch: {
    width: number
    height: number
    fps: number
    input_format: string
    output_format: string
    quality_preset: QualityPresetId
  }) => void
}

export function VdiTeamsReadinessCard({
  sourceFormats,
  virtualCameras,
  selectedVirtualPath,
  onApplyAvdPreset,
}: VdiTeamsReadinessCardProps) {
  const [payload, setPayload] = useState<VdiReadinessPayload | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [diagnosticText, setDiagnosticText] = useState('')
  const [parsedDiagnostic, setParsedDiagnostic] = useState<ParsedAvdDiagnostic | null>(null)

  const load = useCallback(async () => {
    setLoadError(null)
    try {
      const data = await apiGetJson<VdiReadinessPayload>('/api/virtual-camera/vdi-readiness')
      setPayload(data)
    } catch (e: unknown) {
      setLoadError(e instanceof Error ? e.message : 'Could not load VDI readiness')
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const selectedVirtual = useMemo(
    () => virtualCameras.find((c) => c.device_path === selectedVirtualPath),
    [virtualCameras, selectedVirtualPath],
  )

  const applyPreset = (presetId: VdiQualityPresetId) => {
    const patch = applyVdiQualityPreset(presetId, sourceFormats, selectedVirtual?.formats)
    onApplyAvdPreset(patch)
  }

  const applyAvdPreset = () => applyPreset('avd_teams')
  const applyUltraLowPreset = () => applyPreset('vdi_ultra_low')
  const applyMinimalPreset = () => applyPreset('vdi_minimal')

  const parseDiagnostic = () => {
    if (!diagnosticText.trim()) {
      setParsedDiagnostic(null)
      return
    }
    setParsedDiagnostic(parseAvdTeamsDiagnostic(diagnosticText))
  }

  const rdpBlock = (payload?.rdp_property_lines ?? []).join('\n')
  const diagSummary = parsedDiagnostic ? avdDiagnosticSummary(parsedDiagnostic) : null

  return (
    <div className="le-card" style={{ marginBottom: '1rem' }}>
      <h3>Azure Cloud VDI / Teams</h3>
      <p className="forge-support">
        Linux-primary workflow: virtual V4L2 on this machine → AVD client camera redirect → Teams desktop
        in your Cloud PC. Media Foundation virtual cameras are <strong>Windows-only</strong> — not available
        on Ubuntu.
      </p>
      {loadError && (
        <p className="forge-support" style={{ color: 'var(--ks-danger, #c0392b)' }}>{loadError}</p>
      )}
      {payload?.teams_optimization_note && (
        <p className="forge-support">{payload.teams_optimization_note}</p>
      )}
      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.75rem' }}>
        <button type="button" className="le-btn le-btn--primary" onClick={applyAvdPreset}>
          Apply AVD Teams preset
        </button>
        <button type="button" className="le-btn" onClick={applyUltraLowPreset}>
          VDI ultra-low (320×160)
        </button>
        <button type="button" className="le-btn" onClick={applyMinimalPreset}>
          VDI minimal (160×120)
        </button>
        <button type="button" className="le-btn" onClick={() => void load()}>
          Refresh VDI status
        </button>
        {payload?.links?.teams_on_avd && (
          <a className="le-btn" href={payload.links.teams_on_avd} target="_blank" rel="noreferrer">
            Teams on AVD (docs)
          </a>
        )}
      </div>
      {payload?.virtual_devices && payload.virtual_devices.length > 0 && (
        <p className="forge-support" style={{ marginBottom: '0.5rem' }}>
          Virtual device output formats:{' '}
          {(payload.virtual_devices.find((d) => d.device_path === selectedVirtualPath)?.output_format_options ??
            payload.virtual_devices[0]?.output_format_options ??
            []).join(', ') || '—'}
          {payload.virtual_devices.find((d) => d.device_path === selectedVirtualPath)?.vdi_friendly?.mjpeg
            ? ' · MJPEG recommended for RDP redirect'
            : ''}
        </p>
      )}
      {payload?.running_profiles && payload.running_profiles.length > 0 && (
        <p className="forge-support">
          Running:{' '}
          {payload.running_profiles
            .map(
              (p) =>
                `${p.name ?? p.id} (${p.output_format ?? 'YUYV'} ${p.resolution?.width ?? 0}×${p.resolution?.height ?? 0} @ ${p.fps ?? 0})`,
            )
            .join('; ')}
        </p>
      )}
      <TechnicalDetails summary="IT checklist — host pool RDP properties">
        <p className="forge-support">Ask your Azure admin to set these on the Cloud PC host pool:</p>
        <pre className="forge-support" style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem' }}>{rdpBlock}</pre>
        {payload?.links?.rdp_properties && (
          <p className="forge-support">
            <a href={payload.links.rdp_properties} target="_blank" rel="noreferrer">
              Azure RDP properties reference
            </a>
          </p>
        )}
      </TechnicalDetails>
      <div style={{ marginTop: '0.75rem' }}>
        <p className="forge-support" style={{ marginBottom: '0.35rem' }}>
          Cloud PC diagnostic — run <code>scripts/avd-teams-vc-diagnostic.ps1</code> in your Windows session
          (saves to <code>Documents\forge-vc-avd-diagnostic-&lt;timestamp&gt;.txt</code>), then paste file
          contents below:
        </p>
        <textarea
          className="le-input"
          rows={5}
          value={diagnosticText}
          onChange={(e) => setDiagnosticText(e.target.value)}
          placeholder="Paste PowerShell diagnostic output from Cloud PC…"
          style={{ width: '100%', fontFamily: 'monospace', fontSize: '0.8rem' }}
        />
        <button type="button" className="le-btn" style={{ marginTop: '0.35rem' }} onClick={parseDiagnostic}>
          Parse diagnostic
        </button>
        {parsedDiagnostic && diagSummary && (
          <ul className="forge-support" style={{ marginTop: '0.5rem' }}>
            {parsedDiagnostic.checks.map((check) => (
              <li key={check.id}>
                {check.ok ? '✓' : '✗'} {check.label}
                {!check.ok && <span style={{ color: 'var(--ks-danger, #c0392b)' }}> — {check.detail}</span>}
              </li>
            ))}
            <li>
              Score: {diagSummary.pass}/{diagSummary.total} checks matched
            </li>
          </ul>
        )}
      </div>
    </div>
  )
}

export { pickPreferredVdiOutputFormat }
