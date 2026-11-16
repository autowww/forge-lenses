import { useCallback, useState } from 'react'
import type { BootstrapPayload } from '../lib/virtualCameraTypes'

type V4l2LoopbackSetupModalProps = {
  bootstrap: BootstrapPayload
  open: boolean
  onClose: () => void
  onRefresh: () => void
}

async function copyText(text: string): Promise<boolean> {
  const value = text.trim()
  if (!value) return false
  try {
    await navigator.clipboard.writeText(value)
    return true
  } catch {
    try {
      const ta = document.createElement('textarea')
      ta.value = value
      ta.setAttribute('readonly', 'true')
      ta.style.position = 'fixed'
      ta.style.left = '-9999px'
      document.body.appendChild(ta)
      ta.select()
      const ok = document.execCommand('copy')
      document.body.removeChild(ta)
      return ok
    } catch {
      return false
    }
  }
}

function actionLabel(action: string | undefined): string {
  switch (action) {
    case 'install':
      return 'Install v4l2loopback (run in terminal)'
    case 'modprobe':
      return 'Load virtual cameras (run in terminal)'
    default:
      return 'Run in terminal'
  }
}

export function V4l2LoopbackSetupModal({
  bootstrap,
  open,
  onClose,
  onRefresh,
}: V4l2LoopbackSetupModalProps) {
  const [copiedKey, setCopiedKey] = useState<string | null>(null)

  const primary = bootstrap.primary_sudo_command ?? ''
  const cmds = bootstrap.privileged_commands ?? {}

  const handleCopy = useCallback(async (key: string, text: string) => {
    const ok = await copyText(text)
    if (ok) {
      setCopiedKey(key)
      window.setTimeout(() => setCopiedKey(null), 2000)
    }
  }, [])

  if (!open) return null

  return (
    <div
      className="le-vc-loopback-modal-backdrop"
      role="presentation"
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 2000,
        background: 'rgba(0, 0, 0, 0.55)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1rem',
      }}
    >
      <div
        className="le-card le-vc-loopback-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="vc-loopback-setup-title"
        onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: '42rem', width: '100%', maxHeight: '90vh', overflow: 'auto' }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.75rem' }}>
          <h2 id="vc-loopback-setup-title" style={{ margin: 0 }}>v4l2loopback setup required</h2>
          <button type="button" className="le-btn" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>

        <p className="forge-support" style={{ marginTop: '0.75rem' }}>
          {bootstrap.setup_issue_message ?? bootstrap.privilege_note}
        </p>
        <p className="forge-support">{bootstrap.privilege_note}</p>

        {primary && (
          <div style={{ marginTop: '1rem' }}>
            <p className="forge-support" style={{ marginBottom: '0.35rem', fontWeight: 600 }}>
              {actionLabel(bootstrap.primary_sudo_action)}
            </p>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'flex-start' }}>
              <textarea
                className="le-input le-mono"
                readOnly
                rows={3}
                value={primary}
                aria-label="Primary sudo command"
                style={{
                  flex: '1 1 16rem',
                  fontFamily: 'monospace',
                  fontSize: '0.85rem',
                  resize: 'vertical',
                }}
                onFocus={(e) => e.currentTarget.select()}
              />
              <button
                type="button"
                className="le-btn le-btn--primary"
                onClick={() => void handleCopy('primary', primary)}
              >
                {copiedKey === 'primary' ? 'Copied' : 'Copy command'}
              </button>
            </div>
          </div>
        )}

        {cmds.install && bootstrap.primary_sudo_action !== 'install' && (
          <CommandRow
            label="Install packages (if modprobe says module missing)"
            command={cmds.install}
            copyKey="install"
            copiedKey={copiedKey}
            onCopy={handleCopy}
          />
        )}
        {cmds.modprobe && bootstrap.primary_sudo_action !== 'modprobe' && (
          <CommandRow
            label="Load module"
            command={cmds.modprobe}
            copyKey="modprobe-alt"
            copiedKey={copiedKey}
            onCopy={handleCopy}
          />
        )}
        {cmds.persist && (
          <CommandRow
            label="Optional — persist after reboot"
            command={cmds.persist}
            copyKey="persist"
            copiedKey={copiedKey}
            onCopy={handleCopy}
          />
        )}
        {cmds.verify && (
          <CommandRow
            label="Verify virtual cameras"
            command={cmds.verify}
            copyKey="verify"
            copiedKey={copiedKey}
            onCopy={handleCopy}
          />
        )}

        <div
          style={{
            display: 'flex',
            gap: '0.5rem',
            flexWrap: 'wrap',
            marginTop: '1.25rem',
          }}
        >
          <button type="button" className="le-btn le-btn--primary" onClick={onRefresh}>
            I ran this — refresh
          </button>
          <button type="button" className="le-btn" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

function CommandRow({
  label,
  command,
  copyKey,
  copiedKey,
  onCopy,
}: {
  label: string
  command: string
  copyKey: string
  copiedKey: string | null
  onCopy: (key: string, text: string) => void
}) {
  return (
    <div style={{ marginTop: '0.75rem' }}>
      <p className="forge-support" style={{ marginBottom: '0.35rem' }}>{label}</p>
      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'flex-start' }}>
        <textarea
          className="le-input le-mono"
          readOnly
          rows={2}
          value={command}
          style={{
            flex: '1 1 16rem',
            fontFamily: 'monospace',
            fontSize: '0.8rem',
            resize: 'vertical',
          }}
          onFocus={(e) => e.currentTarget.select()}
        />
        <button type="button" className="le-btn" onClick={() => void onCopy(copyKey, command)}>
          {copiedKey === copyKey ? 'Copied' : 'Copy'}
        </button>
      </div>
    </div>
  )
}
