import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { apiGetJson, apiPostJson, apiPutJson, ApiError } from '../api/http'
import { PageHeader, StatePanel, TechnicalDetails } from '../components/page'
import { VdiTeamsReadinessCard } from '../components/VdiTeamsReadinessCard'
import { V4l2LoopbackSetupModal } from '../components/V4l2LoopbackSetupModal'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'
import {
  blurLabel,
  formatDevicePath,
  type BootstrapPayload,
  type CameraDevice,
  type CameraProfile,
  statusLabel,
} from '../lib/virtualCameraTypes'
import {
  applyBalancedPreset,
  applyQualityPreset,
  applyVdiQualityPreset,
  buildEditorCapabilityOptions,
  buildOutputFormatOptions,
  fpsOptionsForEditor,
  isVdiQualityPresetId,
  matchQualityPreset,
  pickPreferredVdiOutputFormat,
  pickSourceDevice,
  type QualityPresetId,
} from '../lib/virtualCameraEditorOptions'

type EditorState = {
  name: string
  source_stable_id: string
  virtual_device_path: string
  virtual_card_label: string
  width: number
  height: number
  fps: number
  input_format: string
  output_format: string
  mirror: boolean
  quality_preset: QualityPresetId
}

const DEFAULT_EDITOR: EditorState = {
  name: 'New camera profile',
  source_stable_id: '',
  virtual_device_path: '',
  virtual_card_label: 'Studio Virtual Camera',
  width: 640,
  height: 360,
  fps: 15,
  input_format: 'MJPEG',
  output_format: 'YUYV',
  mirror: false,
  quality_preset: 'balanced',
}

function stateBadge(state: string | undefined): string {
  const label = statusLabel(state)
  switch (label) {
    case 'RUNNING':
      return '● Running'
    case 'STARTING':
      return '◐ Starting'
    case 'STOPPING':
      return '◐ Stopping'
    case 'ERROR':
      return '⚠ Error'
    default:
      return '○ Stopped'
  }
}

function profileSummaryLine(p: CameraProfile): string {
  const src = p.source?.label || p.source?.device_path || '—'
  const w = p.resolution?.width ?? 0
  const h = p.resolution?.height ?? 0
  const virt = formatDevicePath(p.virtual?.device_path)
  const blur = blurLabel(p.blur_level)
  return `${src} → ${w}×${h} @ ${p.fps ?? 0} · ${blur} → ${virt}`
}

function holderSummary(
  holders: Array<{ pid?: number; command?: string }> | null | undefined,
): string | null {
  if (!holders?.length) return null
  const h = holders[0]
  const pid = h.pid != null ? String(h.pid) : ''
  const cmd = (h.command || '').trim()
  if (pid && cmd) return `PID ${pid} · ${cmd}`
  if (pid) return `PID ${pid}`
  return cmd || null
}

export function VirtualCameraStudioPage() {
  useLensesCopilotPage({
    route: 'virtual-camera',
    defaultQuery: 'Help me configure a virtual camera profile for VDI or Teams.',
  })

  const [enabled, setEnabled] = useState<boolean | null>(null)
  const [profiles, setProfiles] = useState<CameraProfile[]>([])
  const [cameras, setCameras] = useState<{ physical?: CameraDevice[]; virtual?: CameraDevice[] }>({})
  const [bootstrap, setBootstrap] = useState<BootstrapPayload | null>(null)
  const [loopbackSetupOpen, setLoopbackSetupOpen] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [editorOpen, setEditorOpen] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editor, setEditor] = useState<EditorState>(DEFAULT_EDITOR)
  const [previewId, setPreviewId] = useState<string | null>(null)
  const [previewView, setPreviewView] = useState<'processed' | 'source'>('processed')
  const [detailsProfileId, setDetailsProfileId] = useState<string | null>(null)
  const [editorPreviewError, setEditorPreviewError] = useState(false)
  const [livePreviewError, setLivePreviewError] = useState(false)
  const [editorPreviewKey, setEditorPreviewKey] = useState(0)
  const [editorPreviewActiveUrl, setEditorPreviewActiveUrl] = useState<string | null>(null)
  const [previewStreamKey, setPreviewStreamKey] = useState(0)
  const prevPreviewStateRef = useRef<string>('stopped')

  const physicalCameras = cameras.physical ?? []
  const virtualCameras = cameras.virtual ?? []

  const selectedSource = useMemo(
    () => pickSourceDevice(physicalCameras, editor.source_stable_id),
    [physicalCameras, editor.source_stable_id],
  )

  const selectedVirtual = useMemo(
    () => virtualCameras.find((c) => c.device_path === editor.virtual_device_path),
    [virtualCameras, editor.virtual_device_path],
  )

  const editorOptions = useMemo(
    () =>
      buildEditorCapabilityOptions(
        selectedSource?.formats,
        editor.input_format,
        selectedVirtual?.formats,
      ),
    [selectedSource?.formats, editor.input_format, selectedVirtual?.formats],
  )

  const editorFpsOptions = useMemo(
    () =>
      fpsOptionsForEditor(
        selectedSource?.formats,
        editorOptions.resolutions,
        editor.width,
        editor.height,
        editor.input_format,
      ),
    [
      selectedSource?.formats,
      editorOptions.resolutions,
      editor.width,
      editor.height,
      editor.input_format,
    ],
  )

  const activeQualityPreset = useMemo(
    () =>
      matchQualityPreset(
        editorOptions.presets,
        editor.width,
        editor.height,
        editor.fps,
        editor.input_format,
      ),
    [editorOptions.presets, editor.width, editor.height, editor.fps, editor.input_format],
  )

  const fpsSelectValue = editorFpsOptions.includes(editor.fps)
    ? String(editor.fps)
    : String(editorFpsOptions[0] ?? editor.fps)

  const resolutionSelectValue = editorOptions.resolutions.some(
    (r) => r.key === `${editor.width}x${editor.height}`,
  )
    ? `${editor.width}x${editor.height}`
    : (editorOptions.resolutions[0]?.key ?? `${editor.width}x${editor.height}`)

  const loadAll = useCallback(async () => {
    try {
      const [en, prof, cam, boot] = await Promise.all([
        apiGetJson<{ enabled?: boolean }>('/api/virtual-camera/enabled'),
        apiGetJson<{ profiles?: CameraProfile[] }>('/api/virtual-camera/profiles'),
        apiGetJson<{ physical?: CameraDevice[]; virtual?: CameraDevice[] }>('/api/virtual-camera/cameras'),
        apiGetJson<BootstrapPayload>('/api/virtual-camera/bootstrap'),
      ])
      setEnabled(Boolean(en.enabled))
      setProfiles(prof.profiles ?? [])
      setCameras(cam)
      setBootstrap(boot)
      if (boot.ready) {
        setLoopbackSetupOpen(false)
      }
      setError(null)
    } catch (e: unknown) {
      setEnabled(false)
      setError(e instanceof Error ? e.message : 'Failed to load Virtual Camera Studio')
    }
  }, [])

  useEffect(() => {
    void loadAll()
  }, [loadAll])

  useEffect(() => {
    if (bootstrap && !bootstrap.ready) {
      setLoopbackSetupOpen(true)
    }
  }, [bootstrap?.ready])

  const loopbackNotReady = Boolean(bootstrap && !bootstrap.ready)

  const promptLoopbackSetup = useCallback(() => {
    setLoopbackSetupOpen(true)
    setActionError(
      'Virtual cameras are not ready. Run the sudo command in the popup, then click “I ran this — refresh”.',
    )
  }, [])

  useEffect(() => {
    const timer = window.setInterval(() => {
      void loadAll()
    }, 4000)
    return () => window.clearInterval(timer)
  }, [loadAll])

  const openCreate = () => {
    if (loopbackNotReady) {
      promptLoopbackSetup()
      return
    }
    setPreviewId(null)
    setEditingId(null)
    const first = physicalCameras[0]
    const virt = virtualCameras[0]
    const applied = applyBalancedPreset(first?.formats)
    setEditor({
      ...DEFAULT_EDITOR,
      source_stable_id: first?.stable_id ?? '',
      virtual_device_path: virt?.device_path ?? '',
      ...applied,
      output_format: pickPreferredVdiOutputFormat(virt?.formats),
    })
    setEditorOpen(true)
  }

  const openEdit = (p: CameraProfile) => {
    setPreviewId(null)
    setEditingId(p.id)
    const width = p.resolution?.width ?? 640
    const height = p.resolution?.height ?? 360
    const fps = p.fps ?? 15
    const input_format = p.input_format ?? 'MJPEG'
    const src = pickSourceDevice(physicalCameras, p.source?.stable_id ?? '')
    const virt = virtualCameras.find((c) => c.device_path === p.virtual?.device_path)
    const options = buildEditorCapabilityOptions(src?.formats, input_format, virt?.formats)
    const output_format = p.output_format ?? pickPreferredVdiOutputFormat(virt?.formats)
    setEditor({
      name: p.name,
      source_stable_id: p.source?.stable_id ?? '',
      virtual_device_path: p.virtual?.device_path ?? '',
      virtual_card_label: p.virtual?.card_label ?? 'Studio Virtual Camera',
      width,
      height,
      fps,
      input_format,
      output_format,
      mirror: Boolean(p.mirror),
      quality_preset: matchQualityPreset(options.presets, width, height, fps, input_format),
    })
    setEditorOpen(true)
  }

  const saveProfile = async () => {
    setActionError(null)
    const src = pickSourceDevice(physicalCameras, editor.source_stable_id)
    const body = {
      name: editor.name,
      source: {
        stable_id: editor.source_stable_id,
        device_path: src?.device_path ?? '',
        label: src?.label ?? '',
      },
      virtual: {
        device_path: editor.virtual_device_path,
        card_label: editor.virtual_card_label,
      },
      resolution: { width: editor.width, height: editor.height },
      fps: editor.fps,
      input_format: editor.input_format,
      output_format: editor.output_format,
      mirror: editor.mirror,
      blur_level: 'off',
    }
    try {
      if (editingId) {
        await apiPutJson(`/api/virtual-camera/profiles/${encodeURIComponent(editingId)}`, { profile: body })
      } else {
        await apiPostJson('/api/virtual-camera/profiles', { profile: body })
      }
      setEditorOpen(false)
      await loadAll()
    } catch (e: unknown) {
      setActionError(e instanceof ApiError ? e.message : 'Save failed')
    }
  }

  const runAction = async (
    id: string,
    action: 'start' | 'stop' | 'restart' | 'duplicate' | 'delete' | 'force-restart',
    body?: Record<string, unknown>,
  ) => {
    if (loopbackNotReady && (action === 'start' || action === 'restart' || action === 'force-restart')) {
      promptLoopbackSetup()
      return
    }
    setBusyId(id)
    setActionError(null)
    if (action === 'stop' || action === 'restart' || action === 'force-restart') {
      if (previewId === id) setPreviewId(null)
    }
    try {
      await apiPostJson(`/api/virtual-camera/profiles/${encodeURIComponent(id)}/${action}`, body ?? {})
      if (action === 'delete' && previewId === id) setPreviewId(null)
      await loadAll()
    } catch (e: unknown) {
      const msg = e instanceof ApiError ? e.message : `${action} failed`
      setActionError(msg)
    } finally {
      setBusyId(null)
    }
  }

  const forceRestart = (id: string) => {
    const ok = window.confirm(
      'Force restart may terminate other applications using the camera. Only continue if you accept that risk.',
    )
    if (!ok) return
    void runAction(id, 'force-restart', { confirm: true })
  }

  useEffect(() => {
    if (!editorOpen) {
      const dev = selectedSource?.device_path
      if (dev) {
        void apiPostJson('/api/virtual-camera/preview/stop', { device: dev }).catch(() => {})
      }
      setEditorPreviewActiveUrl(null)
      return
    }
    const dev = selectedSource?.device_path
    if (!dev) {
      setEditorPreviewActiveUrl(null)
      return
    }
    const q = new URLSearchParams({
      device: dev,
      width: String(editor.width),
      height: String(editor.height),
      fps: String(editor.fps),
      input_format: editor.input_format,
    })
    const nextUrl = `/api/virtual-camera/preview/_source?${q.toString()}`
    let cancelled = false
    void apiPostJson('/api/virtual-camera/preview/stop', { device: dev })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) {
          setEditorPreviewError(false)
          setEditorPreviewActiveUrl(nextUrl)
          setEditorPreviewKey((k) => k + 1)
        }
      })
    return () => {
      cancelled = true
    }
  }, [
    editorOpen,
    selectedSource?.device_path,
    editor.width,
    editor.height,
    editor.fps,
    editor.input_format,
  ])

  useEffect(() => {
    if (previewId) setPreviewStreamKey((k) => k + 1)
  }, [previewId, previewView])

  const previewUrl =
    previewId && previewView
      ? `/api/virtual-camera/preview/${encodeURIComponent(previewId)}?view=${previewView}&k=${previewStreamKey}`
      : null

  const detailsProfile = detailsProfileId ? profiles.find((p) => p.id === detailsProfileId) : null
  const previewProfile = previewId ? profiles.find((p) => p.id === previewId) : null
  const previewRuntimeState = previewProfile?.runtime?.state ?? 'stopped'
  const showProcessedPreview =
    previewView === 'processed' && previewRuntimeState === 'running'
  const showSourcePreview =
    previewView === 'source' && previewRuntimeState !== 'running'

  const editingProfile = editingId ? profiles.find((p) => p.id === editingId) : null
  const editingPipelineRunning =
    editingProfile?.runtime?.state === 'running' || editingProfile?.runtime?.state === 'starting'

  useEffect(() => {
    setLivePreviewError(false)
  }, [previewId, previewStreamKey, previewView])

  useEffect(() => {
    if (!previewId) {
      prevPreviewStateRef.current = 'stopped'
      return
    }
    if (previewRuntimeState === 'running' && prevPreviewStateRef.current !== 'running') {
      setPreviewStreamKey((k) => k + 1)
    }
    prevPreviewStateRef.current = previewRuntimeState
  }, [previewId, previewRuntimeState])

  if (enabled === null) {
    return <StatePanel variant="loading" title="Virtual Camera Studio" description="Loading…" />
  }

  if (!enabled) {
    return (
      <StatePanel
        variant="empty"
        title="Virtual Camera Studio"
        description="This lab is disabled. Set LENSES_EXPERIMENTAL_VIRTUAL_CAMERA=1 and restart Studio Desktop."
      />
    )
  }

  return (
    <>
      <PageHeader
        title="Virtual Camera Studio"
        subtitle="Create local virtual V4L2 cameras from physical webcams for VDI, browsers, and conferencing apps."
      />

      {error && (
        <p className="forge-support" style={{ color: 'var(--ks-danger, #c0392b)' }}>
          {error}
        </p>
      )}

      {bootstrap && !bootstrap.ready && (
        <div className="le-card" style={{ marginBottom: '1rem' }}>
          <h3>v4l2loopback setup required</h3>
          <p className="forge-support">
            {bootstrap.setup_issue_message ?? bootstrap.privilege_note}
          </p>
          <button type="button" className="le-btn le-btn--primary" onClick={() => setLoopbackSetupOpen(true)}>
            Show sudo setup commands
          </button>
        </div>
      )}

      {bootstrap && (
        <V4l2LoopbackSetupModal
          bootstrap={bootstrap}
          open={loopbackSetupOpen && !bootstrap.ready}
          onClose={() => setLoopbackSetupOpen(false)}
          onRefresh={() => void loadAll()}
        />
      )}

      {actionError && (
        <p className="forge-support" style={{ color: 'var(--ks-danger, #c0392b)' }}>
          {actionError}
        </p>
      )}

      <VdiTeamsReadinessCard
        sourceFormats={selectedSource?.formats ?? physicalCameras[0]?.formats}
        virtualCameras={virtualCameras}
        selectedVirtualPath={editor.virtual_device_path || virtualCameras[0]?.device_path || ''}
        onApplyAvdPreset={(patch) => {
          setPreviewId(null)
          setEditingId(null)
          const first = physicalCameras[0]
          const virtPath = editor.virtual_device_path || virtualCameras[0]?.device_path || ''
          setEditor({
            ...DEFAULT_EDITOR,
            source_stable_id: first?.stable_id ?? editor.source_stable_id,
            virtual_device_path: virtPath,
            ...patch,
          })
          setEditorOpen(true)
        }}
      />

      <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
        <button type="button" className="le-btn le-btn--primary" onClick={openCreate}>
          New profile
        </button>
        <button type="button" className="le-btn" onClick={() => void loadAll()}>
          Refresh
        </button>
      </div>

      <h2 style={{ marginBottom: '0.5rem' }}>Camera profiles</h2>
      {profiles.length === 0 && (
        <p className="forge-support">No profiles yet. Create one to map a physical camera to a virtual device.</p>
      )}

      {profiles.map((p) => {
        const state = p.runtime?.state ?? 'stopped'
        const isBusy = busyId === p.id
        const holderLine = holderSummary(p.runtime?.source_busy_holder)
        const isError = state === 'error'
        return (
          <div key={p.id} className="le-card" style={{ marginBottom: '0.75rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
              <div>
                <h3 style={{ margin: 0 }}>
                  {p.name}{' '}
                  <span className="forge-support" style={{ fontWeight: 600 }}>
                    {statusLabel(state)}
                  </span>
                </h3>
                <p className="forge-support" style={{ margin: '0.25rem 0' }}>{profileSummaryLine(p)}</p>
                <p className="forge-support" style={{ margin: 0 }}>
                  {stateBadge(state)}
                  {p.runtime?.pid != null && ` · PID ${p.runtime.pid}`}
                  {p.runtime?.elapsed_seconds != null && state === 'running' && ` · ${p.runtime.elapsed_seconds}s`}
                </p>
                {isError && p.runtime?.last_error && (
                  <p className="forge-support" style={{ color: 'var(--ks-danger, #c0392b)', marginTop: '0.35rem' }}>
                    {p.runtime.error_code ? `${p.runtime.error_code}: ` : ''}
                    {p.runtime.last_error}
                  </p>
                )}
                {isError && holderLine && (
                  <p className="forge-support" style={{ margin: 0 }}>{holderLine}</p>
                )}
              </div>
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'flex-start' }}>
                {state === 'running' ? (
                  <>
                    <button type="button" className="le-btn" disabled={isBusy} onClick={() => void runAction(p.id, 'stop')}>
                      Stop
                    </button>
                    <button type="button" className="le-btn" disabled={isBusy} onClick={() => void runAction(p.id, 'restart')}>
                      Restart
                    </button>
                    <button
                      type="button"
                      className="le-btn"
                      onClick={() => {
                        setPreviewId(p.id)
                        setPreviewView('processed')
                      }}
                    >
                      Preview
                    </button>
                  </>
                ) : isError ? (
                  <>
                    <button type="button" className="le-btn le-btn--primary" disabled={isBusy} onClick={() => void runAction(p.id, 'start')}>
                      Retry
                    </button>
                    <button type="button" className="le-btn" disabled={isBusy} onClick={() => forceRestart(p.id)}>
                      Force restart
                    </button>
                    <button type="button" className="le-btn" onClick={() => setDetailsProfileId(p.id)}>
                      Details
                    </button>
                  </>
                ) : (
                  <>
                    <button type="button" className="le-btn le-btn--primary" disabled={isBusy} onClick={() => void runAction(p.id, 'start')}>
                      Start
                    </button>
                    <button
                      type="button"
                      className="le-btn"
                      onClick={() => {
                        setPreviewId(p.id)
                        setPreviewView('source')
                      }}
                    >
                      Preview
                    </button>
                  </>
                )}
                <button type="button" className="le-btn" disabled={isBusy} onClick={() => openEdit(p)}>
                  Edit
                </button>
                <button type="button" className="le-btn" disabled={isBusy} onClick={() => void runAction(p.id, 'duplicate')}>
                  Duplicate
                </button>
                <button type="button" className="le-btn" disabled={isBusy} onClick={() => void runAction(p.id, 'delete')}>
                  Delete
                </button>
              </div>
            </div>
          </div>
        )
      })}

      {detailsProfile && (
        <div className="le-card" style={{ marginTop: '1rem' }}>
          <h3>Diagnostics — {detailsProfile.name}</h3>
          <TechnicalDetails summary="Pipeline diagnostics">
            <pre className="forge-support" style={{ whiteSpace: 'pre-wrap', fontSize: '0.8rem' }}>
              {detailsProfile.runtime?.stderr_tail || detailsProfile.runtime?.last_error || 'No diagnostics recorded.'}
            </pre>
          </TechnicalDetails>
          <button type="button" className="le-btn" style={{ marginTop: '0.5rem' }} onClick={() => setDetailsProfileId(null)}>
            Close
          </button>
        </div>
      )}

      {previewId && (
        <div className="le-card" style={{ marginTop: '1rem' }}>
          <h3>Live preview</h3>
          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem', flexWrap: 'wrap' }}>
            <button
              type="button"
              className={previewView === 'processed' ? 'le-btn le-btn--primary' : 'le-btn'}
              onClick={() => setPreviewView('processed')}
            >
              Processed
            </button>
            <button
              type="button"
              className={previewView === 'source' ? 'le-btn le-btn--primary' : 'le-btn'}
              onClick={() => setPreviewView('source')}
            >
              Original
            </button>
            {previewRuntimeState === 'running' && (
              <>
                <button
                  type="button"
                  className="le-btn"
                  disabled={busyId === previewId}
                  onClick={() => void runAction(previewId, 'stop')}
                >
                  Stop
                </button>
                <button
                  type="button"
                  className="le-btn"
                  disabled={busyId === previewId}
                  onClick={() => void runAction(previewId, 'restart')}
                >
                  Restart
                </button>
              </>
            )}
            {previewRuntimeState === 'stopped' && (
              <button
                type="button"
                className="le-btn le-btn--primary"
                disabled={busyId === previewId}
                onClick={() => void runAction(previewId, 'start')}
              >
                Start
              </button>
            )}
            <button type="button" className="le-btn" onClick={() => setPreviewId(null)}>
              Close
            </button>
          </div>
          {previewUrl && (showProcessedPreview || showSourcePreview) ? (
            <img
              key={previewStreamKey}
              src={previewUrl}
              alt="Camera preview"
              onError={() => setLivePreviewError(true)}
              onLoad={() => setLivePreviewError(false)}
              style={{
                maxWidth: '100%',
                minHeight: '120px',
                background: '#111',
                border: '1px solid var(--ks-border, #ccc)',
              }}
            />
          ) : null}
          {livePreviewError && (showProcessedPreview || showSourcePreview) && (
            <p className="forge-support" style={{ color: 'var(--ks-danger, #c0392b)' }}>
              Preview stream failed — try Restart on the profile or close other apps using the camera.
            </p>
          )}
          {previewView === 'processed' && previewRuntimeState === 'stopped' && (
            <p className="forge-support">
              Processed preview needs a running pipeline. Click <strong>Start</strong> above (or on the profile
              card), then stay on Processed.
            </p>
          )}
          {previewView === 'processed' && previewRuntimeState === 'starting' && (
            <p className="forge-support">Pipeline is starting — preview will appear when RUNNING.</p>
          )}
          {previewView === 'processed' && previewRuntimeState === 'stopping' && (
            <p className="forge-support">Preview paused while the pipeline is stopping.</p>
          )}
          {previewView === 'source' && (
            <p className="forge-support">
              {previewRuntimeState === 'running'
                ? 'Original preview is unavailable while the pipeline is running. Use Processed (tee from the same pipeline).'
                : 'Original preview uses a separate capture only when the pipeline is stopped. While running, use Processed (tee from the same pipeline).'}
            </p>
          )}
        </div>
      )}

      {editorOpen && (
        <div className="le-card" style={{ marginTop: '1rem' }}>
          <h3>{editingId ? 'Edit profile' : 'New profile'}</h3>
          <label className="forge-support">
            Name
            <input
              className="le-input"
              value={editor.name}
              onChange={(e) => setEditor((s) => ({ ...s, name: e.target.value }))}
            />
          </label>
          <label className="forge-support" style={{ display: 'block', marginTop: '0.5rem' }}>
            Source camera
            <select
              className="le-input"
              value={editor.source_stable_id}
              onChange={(e) => {
                const stableId = e.target.value
                const cam = pickSourceDevice(physicalCameras, stableId)
                const applied = applyBalancedPreset(cam?.formats)
                setEditor((s) => ({
                  ...s,
                  source_stable_id: stableId,
                  ...applied,
                }))
              }}
            >
              <option value="">Select…</option>
              {physicalCameras.map((c) => (
                <option key={c.stable_id ?? c.device_path} value={c.stable_id ?? ''}>
                  {c.label} ({c.device_path}){c.busy ? ' — busy' : ''}
                </option>
              ))}
            </select>
          </label>
          {selectedSource?.formats && selectedSource.formats.length > 0 && (
            <p className="forge-support">
              Formats: {selectedSource.formats.map((f) => f.fourcc).filter(Boolean).join(', ')}
            </p>
          )}
          {editorPreviewActiveUrl ? (
            <div style={{ marginTop: '0.75rem' }}>
              <p className="forge-support" style={{ marginBottom: '0.35rem' }}>Source preview</p>
              {editingPipelineRunning ? (
                <p className="forge-support" style={{ color: 'var(--ks-danger, #c0392b)' }}>
                  Source preview is unavailable while this profile is running — the camera is owned by the
                  pipeline. Stop the profile or use Live preview → Processed.
                </p>
              ) : null}
              {selectedSource?.busy && !editingPipelineRunning ? (
                <p className="forge-support" style={{ color: 'var(--ks-danger, #c0392b)' }}>
                  Camera is in use by another app — close Teams, browser, or other capture tools, then click Refresh.
                </p>
              ) : null}
              {editorPreviewError && !editingPipelineRunning && !selectedSource?.busy ? (
                <p className="forge-support" style={{ color: 'var(--ks-danger, #c0392b)' }}>
                  Preview failed — try another preset or resolution, or click Refresh after closing other camera apps.
                </p>
              ) : null}
              {!selectedSource?.busy && !editingPipelineRunning ? (
                <img
                  key={editorPreviewKey}
                  src={`${editorPreviewActiveUrl}&k=${editorPreviewKey}`}
                  alt="Source camera preview"
                  onError={() => setEditorPreviewError(true)}
                  onLoad={() => setEditorPreviewError(false)}
                  style={{
                    maxWidth: '100%',
                    maxHeight: '240px',
                    minHeight: '120px',
                    background: '#111',
                    border: '1px solid var(--ks-border, #ccc)',
                  }}
                />
              ) : null}
            </div>
          ) : null}
          <label className="forge-support" style={{ display: 'block', marginTop: '0.5rem' }}>
            Virtual device
            <select
              className="le-input"
              value={editor.virtual_device_path}
              onChange={(e) => {
                const virtual_device_path = e.target.value
                const virt = virtualCameras.find((c) => c.device_path === virtual_device_path)
                const outputs = buildOutputFormatOptions(virt?.formats)
                setEditor((s) => ({
                  ...s,
                  virtual_device_path,
                  output_format: outputs.includes(s.output_format)
                    ? s.output_format
                    : pickPreferredVdiOutputFormat(virt?.formats),
                }))
              }}
            >
              <option value="">Select…</option>
              {virtualCameras.map((c) => (
                <option key={c.device_path} value={c.device_path ?? ''}>
                  {c.label} ({c.device_path})
                </option>
              ))}
            </select>
          </label>
          <label className="forge-support" style={{ display: 'block', marginTop: '0.75rem' }}>
            Quality preset
            <select
              className="le-input"
              value={activeQualityPreset === 'custom' ? 'custom' : editor.quality_preset}
              onChange={(e) => {
                const id = e.target.value as QualityPresetId
                if (id === 'custom') return
                if (isVdiQualityPresetId(id)) {
                  setEditor((s) => ({
                    ...s,
                    ...applyVdiQualityPreset(id, selectedSource?.formats, selectedVirtual?.formats),
                  }))
                  return
                }
                const preset = editorOptions.presets.find((p) => p.id === id)
                if (!preset) return
                setEditor((s) => ({ ...s, ...applyQualityPreset(preset) }))
              }}
            >
              {editorOptions.presets.map((preset) => (
                <option key={preset.id} value={preset.id}>
                  {preset.label}
                </option>
              ))}
              {activeQualityPreset === 'custom' && (
                <option value="custom">Custom (manual selection)</option>
              )}
            </select>
            <span className="forge-support" style={{ display: 'block', marginTop: '0.25rem' }}>
              {activeQualityPreset === 'custom'
                ? 'Resolution, FPS, or format no longer matches a preset — adjust preset or fine-tune below.'
                : editorOptions.presets.find((p) => p.id === activeQualityPreset)?.hint}
            </span>
          </label>
          <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem', flexWrap: 'wrap' }}>
            <label className="forge-support">
              Resolution
              <select
                className="le-input"
                value={resolutionSelectValue}
                onChange={(e) => {
                  const [w, h] = e.target.value.split('x').map((n) => Number(n))
                  const fpsChoices = fpsOptionsForEditor(
                    selectedSource?.formats,
                    editorOptions.resolutions,
                    w,
                    h,
                    editor.input_format,
                  )
                  const fps = fpsChoices.includes(editor.fps) ? editor.fps : fpsChoices[0] ?? 15
                  setEditor((s) => ({
                    ...s,
                    width: w,
                    height: h,
                    fps,
                    quality_preset: 'custom',
                  }))
                }}
              >
                {editorOptions.resolutions.map((res) => (
                  <option key={res.key} value={res.key}>
                    {res.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="forge-support">
              FPS
              <select
                className="le-input"
                value={fpsSelectValue}
                onChange={(e) =>
                  setEditor((s) => ({
                    ...s,
                    fps: Number(e.target.value),
                    quality_preset: 'custom',
                  }))
                }
              >
                {editorFpsOptions.map((fps) => (
                  <option key={fps} value={fps}>
                    {fps}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem', flexWrap: 'wrap' }}>
            <label className="forge-support">
              Input format
              <select
                className="le-input"
                value={editor.input_format}
                onChange={(e) => {
                  const input_format = e.target.value
                  const options = buildEditorCapabilityOptions(
                    selectedSource?.formats,
                    input_format,
                    selectedVirtual?.formats,
                  )
                  const res =
                    options.resolutions.find(
                      (r) => r.width === editor.width && r.height === editor.height,
                    ) ?? options.resolutions[0]
                  const fpsChoices = fpsOptionsForEditor(
                    selectedSource?.formats,
                    options.resolutions,
                    res.width,
                    res.height,
                    input_format,
                  )
                  setEditor((s) => ({
                    ...s,
                    input_format,
                    width: res.width,
                    height: res.height,
                    fps: fpsChoices.includes(s.fps) ? s.fps : fpsChoices[0] ?? 15,
                    quality_preset: 'custom',
                  }))
                }}
              >
                {editorOptions.inputFormats.map((fmt) => (
                  <option key={fmt} value={fmt}>
                    {fmt}
                  </option>
                ))}
              </select>
            </label>
            <label className="forge-support">
              Output format
              <select
                className="le-input"
                value={editor.output_format}
                onChange={(e) =>
                  setEditor((s) => ({ ...s, output_format: e.target.value, quality_preset: 'custom' }))
                }
              >
                {editorOptions.outputFormats.map((fmt) => (
                  <option key={fmt} value={fmt}>
                    {fmt}
                  </option>
                ))}
              </select>
              {editor.output_format === 'MJPEG' && (
                <span className="forge-support" style={{ display: 'block', marginTop: '0.25rem' }}>
                  MJPEG on the virtual device can reduce RDP camera redirect artifacts on Azure VDI.
                </span>
              )}
            </label>
          </div>
          <label className="forge-support" style={{ display: 'block', marginTop: '0.5rem' }}>
            Virtual card label
            <input
              className="le-input"
              value={editor.virtual_card_label}
              onChange={(e) => setEditor((s) => ({ ...s, virtual_card_label: e.target.value }))}
            />
          </label>
          <label className="forge-support" style={{ display: 'block', marginTop: '0.5rem' }}>
            <input
              type="checkbox"
              checked={editor.mirror}
              onChange={(e) => setEditor((s) => ({ ...s, mirror: e.target.checked }))}
            />
            Mirror horizontally
          </label>
          <div style={{ marginTop: '0.75rem', display: 'flex', gap: '0.5rem' }}>
            <button type="button" className="le-btn le-btn--primary" onClick={() => void saveProfile()}>
              Save
            </button>
            <button type="button" className="le-btn" onClick={() => setEditorOpen(false)}>
              Cancel
            </button>
          </div>
        </div>
      )}
    </>
  )
}
