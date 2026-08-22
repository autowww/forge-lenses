import { useCallback, useEffect, useMemo, useState } from 'react'
import { apiGetBlob } from '../api/http'
import {
  postWizardCursorLaunchPackExport,
  postWizardCursorLaunchPackPreview,
  type WizardCursorLaunchPackPreviewResponse,
} from '../api/blueprintsWizard'
import type { ArtifactGenerationJson, ClosureOption } from './wizardDomainTypes'
import { ARTIFACT_SLICE_KEYS, CLOSURE_OPTIONS } from './wizardDomainTypes'
import { CLOSURE_OPTION_UI } from './scopeSelectionStep'

function artifactKeysWithRecords(gen: ArtifactGenerationJson | undefined): string[] {
  const arts = gen?.artifacts
  if (!arts || typeof arts !== 'object') return []
  return ARTIFACT_SLICE_KEYS.filter((k) => {
    const rec = (arts as Record<string, unknown>)[k]
    return rec !== undefined && rec !== null && typeof rec === 'object'
  })
}

function downloadBlobZip(filename: string, blob: Blob) {
  const a = document.createElement('a')
  const url = URL.createObjectURL(blob)
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

function downloadBase64Zip(filename: string, b64: string) {
  const bin = atob(b64)
  const bytes = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i)
  downloadBlobZip(filename, new Blob([bytes], { type: 'application/zip' }))
}

type Props = {
  sessionId: string
  artifactGeneration?: ArtifactGenerationJson
  closureOptionsDefault: ClosureOption[]
  disabled?: boolean
}

export function ExperimentalBuildStepPanel({
  sessionId,
  artifactGeneration,
  closureOptionsDefault,
  disabled = false,
}: Props) {
  const available = useMemo(() => artifactKeysWithRecords(artifactGeneration), [artifactGeneration])
  const [selected, setSelected] = useState<Set<string>>(() => new Set())
  const [closure, setClosure] = useState<Set<string>>(
    () => new Set(closureOptionsDefault.length ? closureOptionsDefault : ['exact_only']),
  )

  useEffect(() => {
    setSelected((prev) => {
      if (prev.size === 0 && available.length > 0) return new Set(available)
      const n = new Set(prev)
      for (const k of available) n.add(k)
      return n
    })
  }, [available])

  const [preview, setPreview] = useState<WizardCursorLaunchPackPreviewResponse | null>(null)
  const [exportPath, setExportPath] = useState<string | null>(null)
  const [lastExportWarnings, setLastExportWarnings] = useState<string[] | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [strictApproval, setStrictApproval] = useState(false)
  const [preferStreamDownload, setPreferStreamDownload] = useState(false)

  const toggleKey = (k: string) => {
    setSelected((prev) => {
      const n = new Set(prev)
      if (n.has(k)) n.delete(k)
      else n.add(k)
      return n
    })
  }

  const toggleClosure = (co: ClosureOption) => {
    setClosure((prev) => {
      const n = new Set(prev)
      if (co === 'exact_only') {
        return new Set(['exact_only'])
      }
      n.delete('exact_only')
      if (n.has(co)) n.delete(co)
      else n.add(co)
      return n
    })
  }

  const selectedList = useMemo(() => {
    const allow = new Set(ARTIFACT_SLICE_KEYS as readonly string[])
    return [...selected].filter((k) => allow.has(k))
  }, [selected])
  const closureList = useMemo(
    () => CLOSURE_OPTIONS.filter((c) => closure.has(c)) as string[],
    [closure],
  )

  const canRun = selectedList.length > 0

  const runPreview = useCallback(async () => {
    if (!canRun) return
    setError(null)
    setBusy(true)
    setPreview(null)
    try {
      const r = await postWizardCursorLaunchPackPreview(sessionId, {
        artifact_keys: selectedList,
        closure_options: closureList,
        strict_approval: strictApproval,
      })
      if (!r.ok) {
        if (r.error === 'strict_approval_failed' && Array.isArray(r.artifact_keys) && r.artifact_keys.length) {
          setError(`Strict approval: not approved/locked — ${r.artifact_keys.join(', ')}`)
        } else {
          setError(r.error || 'Preview failed')
        }
        return
      }
      setLastExportWarnings(r.warnings && r.warnings.length > 0 ? r.warnings : null)
      setPreview(r)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Preview failed')
    } finally {
      setBusy(false)
    }
  }, [sessionId, selectedList, closureList, canRun, strictApproval])

  const runExportWorkspace = useCallback(async () => {
    if (!canRun) return
    setError(null)
    setBusy(true)
    setExportPath(null)
    try {
      const r = await postWizardCursorLaunchPackExport(sessionId, {
        artifact_keys: selectedList,
        closure_options: closureList,
        destination: 'workspace',
        strict_approval: strictApproval,
      })
      if (!r.ok) {
        if (r.error === 'strict_approval_failed' && Array.isArray(r.artifact_keys) && r.artifact_keys.length) {
          setError(`Strict approval: not approved/locked — ${r.artifact_keys.join(', ')}`)
        } else {
          setError(r.error || r.detail || 'Export failed')
        }
        return
      }
      setLastExportWarnings(r.warnings && r.warnings.length > 0 ? r.warnings : null)
      if (r.export_path_relative) setExportPath(r.export_path_relative)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Export failed')
    } finally {
      setBusy(false)
    }
  }, [sessionId, selectedList, closureList, canRun, strictApproval])

  const runExportDownload = useCallback(async () => {
    if (!canRun) return
    setError(null)
    setBusy(true)
    try {
      const r = await postWizardCursorLaunchPackExport(sessionId, {
        artifact_keys: selectedList,
        closure_options: closureList,
        destination: 'download',
        strict_approval: strictApproval,
        stream: preferStreamDownload,
      })
      if (!r.ok) {
        if (r.error === 'strict_approval_failed' && Array.isArray(r.artifact_keys) && r.artifact_keys.length) {
          setError(`Strict approval: not approved/locked — ${r.artifact_keys.join(', ')}`)
        } else {
          setError(r.error || r.detail || 'Download failed')
        }
        return
      }
      const fn = r.filename || 'cursor-launch-pack.zip'
      if (r.download_mode === 'stream' && r.download_path) {
        setLastExportWarnings(r.warnings && r.warnings.length > 0 ? r.warnings : null)
        const blob = await apiGetBlob(r.download_path)
        downloadBlobZip(fn, blob)
        return
      }
      if (r.content_base64) {
        setLastExportWarnings(r.warnings && r.warnings.length > 0 ? r.warnings : null)
        downloadBase64Zip(fn, r.content_base64)
        return
      }
      setError('Download failed: empty response')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Download failed')
    } finally {
      setBusy(false)
    }
  }, [sessionId, selectedList, closureList, canRun, strictApproval, preferStreamDownload])

  return (
    <section className="forge-support" aria-labelledby="bpw-experimental-build-heading">
      <h2 id="bpw-experimental-build-heading" className="forge-support" style={{ fontSize: '1.15rem', fontWeight: 600 }}>
        Experimental Build — Cursor Launch Pack
      </h2>
      <p className="forge-support" style={{ marginTop: '0.5rem' }}>
        Compile a markdown-first launch pack from approved artifacts and scope closure options. Preview the file tree,
        then export to the workspace or download a zip. Cursor is not launched from Lenses.
      </p>

      {available.length === 0 ? (
        <p className="forge-support" role="status" style={{ marginTop: '0.75rem' }}>
          No generated artifact slices yet — complete <strong>Review & Generate</strong> first so at least one slice has
          content, then return here.
        </p>
      ) : null}

      {error && (
        <p className="forge-support" role="alert" style={{ marginTop: '0.75rem', color: 'var(--le-danger, #c62828)' }}>
          {error}
        </p>
      )}

      <div style={{ marginTop: '1rem' }}>
        <h3 className="forge-support" style={{ fontSize: '1rem', fontWeight: 600 }}>
          Artifact slices (base selection)
        </h3>
        <p className="forge-support" style={{ marginTop: '0.35rem', fontSize: '0.9rem' }}>
          Keys with generated content are pre-selected. Adjust before preview or export.
        </p>
        <div
          className="ks-wizard-flow__checkbox-grid"
          style={{ marginTop: '0.5rem', display: 'flex', flexWrap: 'wrap', gap: '0.35rem 1rem' }}
        >
          {ARTIFACT_SLICE_KEYS.map((k) => (
            <label key={k} className="forge-support" style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
              <input
                type="checkbox"
                checked={selected.has(k)}
                disabled={disabled || busy}
                onChange={() => toggleKey(k)}
              />
              <span>{k}</span>
            </label>
          ))}
        </div>
      </div>

      <div style={{ marginTop: '1rem' }}>
        <label className="forge-support" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <input
            type="checkbox"
            checked={strictApproval}
            disabled={disabled || busy}
            onChange={(e) => setStrictApproval(e.target.checked)}
          />
          <span>
            Strict approval — block preview/export unless every expanded slice is approved or locked (including
            upstream additions from closure)
          </span>
        </label>
      </div>

      <div style={{ marginTop: '1rem' }}>
        <label className="forge-support" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <input
            type="checkbox"
            checked={preferStreamDownload}
            disabled={disabled || busy}
            onChange={(e) => setPreferStreamDownload(e.target.checked)}
          />
          <span>Prefer streaming download (staged file GET) — also used automatically for packs larger than 8MB</span>
        </label>
      </div>

      <div style={{ marginTop: '1rem' }}>
        <h3 className="forge-support" style={{ fontSize: '1rem', fontWeight: 600 }}>
          Scope closure
        </h3>
        <div style={{ marginTop: '0.5rem', display: 'flex', flexDirection: 'column', gap: 6 }}>
          {CLOSURE_OPTIONS.map((co) => (
            <label key={co} className="forge-support" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <input
                type="checkbox"
                checked={closure.has(co)}
                disabled={disabled || busy}
                onChange={() => toggleClosure(co)}
              />
              <span>{CLOSURE_OPTION_UI[co] ?? co}</span>
            </label>
          ))}
        </div>
      </div>

      <div style={{ marginTop: '1rem', display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
        <button
          type="button"
          className="le-button le-button--primary"
          disabled={disabled || busy || !canRun}
          onClick={runPreview}
        >
          {busy ? 'Working…' : 'Preview tree'}
        </button>
        <button type="button" className="le-button" disabled={disabled || busy || !canRun} onClick={runExportWorkspace}>
          Export to workspace
        </button>
        <button type="button" className="le-button" disabled={disabled || busy || !canRun} onClick={runExportDownload}>
          Download .zip
        </button>
      </div>

      {exportPath && (
        <p className="forge-support" style={{ marginTop: '0.75rem' }}>
          Last export path (under workspace root): <code>{exportPath}</code>
        </p>
      )}

      {lastExportWarnings && lastExportWarnings.length > 0 ? (
        <div className="forge-support" style={{ marginTop: '0.75rem' }}>
          <strong>Export warnings</strong>
          <ul style={{ margin: '0.35rem 0 0 1rem' }}>
            {lastExportWarnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {preview?.warnings && preview.warnings.length > 0 && (
        <div className="forge-support" style={{ marginTop: '0.75rem' }}>
          <strong>Warnings</strong>
          <ul style={{ margin: '0.35rem 0 0 1rem' }}>
            {preview.warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {preview?.files && preview.files.length > 0 && (
        <div className="forge-support" style={{ marginTop: '0.75rem' }}>
          <strong>Pack files ({preview.files.length})</strong>
          <ul
            className="le-launch-pack-tree"
            style={{ margin: '0.35rem 0 0 1rem', maxHeight: '18rem', overflow: 'auto', fontSize: '0.9rem' }}
          >
            {preview.files
              .slice()
              .sort((a, b) => a.path.localeCompare(b.path))
              .map((f) => (
                <li key={f.path}>
                  <code>{f.path}</code> — {f.size} bytes
                </li>
              ))}
          </ul>
        </div>
      )}
    </section>
  )
}
