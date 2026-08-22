/** Matches ``KeyInfo`` from LlmSettingsForm (kept local to avoid circular imports). */
export type LlmProviderKeyInfo = {
  set?: boolean
  preview?: string
  from_file?: boolean
  from_env?: boolean
  env_hint?: string
}

export function LlmProviderKeyField({
  label,
  fieldKey,
  keyInfo,
  value,
  onChange,
  lastOk,
  tryOut,
}: {
  label: string
  fieldKey: 'openai' | 'anthropic' | 'gemini' | 'openai_compatible'
  keyInfo?: LlmProviderKeyInfo
  value: string
  onChange: (v: string) => void
  lastOk?: string
  tryOut?: { onClick: () => void; disabled?: boolean }
}) {
  const set = Boolean(keyInfo?.set)
  const preview = (keyInfo?.preview || '').trim()
  const fromFile = keyInfo?.from_file === true
  const fromEnv = keyInfo?.from_env === true
  const envHint = (keyInfo?.env_hint || '').trim()
  const legacySource =
    keyInfo?.from_file === undefined && keyInfo?.from_env === undefined && set
  const placeholder = !set
    ? 'Paste API key'
    : fromEnv && !fromFile
      ? `•••••••• (from ${envHint || 'environment'} — paste here to save in settings file)`
      : '•••••••• (saved — type only to replace)'
  const sourceHint =
    set &&
    (legacySource ? (
      <>
        Key is configured (settings file and/or environment). Preview:{' '}
        <code className="le-mono">{preview || 'set (hidden)'}</code>
      </>
    ) : fromFile && fromEnv ? (
      <>
        Key saved in <strong>settings file</strong> (overrides env). Preview:{' '}
        <code className="le-mono">{preview || 'set (hidden)'}</code>
      </>
    ) : fromFile ? (
      <>
        Key saved in <strong>settings file</strong>. Preview: <code className="le-mono">{preview || 'set (hidden)'}</code>
      </>
    ) : fromEnv ? (
      <>
        Key from environment (<code className="le-mono">{envHint || 'see README'}</code>) — not stored in the settings
        file. Preview: <code className="le-mono">{preview || 'set (hidden)'}</code>
      </>
    ) : (
      <>
        Preview: <code className="le-mono">{preview || 'set (hidden)'}</code>
      </>
    ))
  return (
    <div style={{ marginBottom: '0.65rem' }}>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: '0.5rem', flexWrap: 'wrap' }}>
        <label className="forge-support" style={{ display: 'block', flex: '1 1 16rem', minWidth: '12rem' }}>
          {label}
          <input
            type="password"
            className="le-input"
            style={{ display: 'block', width: '100%', maxWidth: '28rem', marginTop: '0.2rem' }}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            autoComplete="off"
            aria-describedby={`hint-${fieldKey}`}
          />
        </label>
        {tryOut ? (
          <button
            type="button"
            className="le-btn le-btn--secondary"
            disabled={tryOut.disabled}
            onClick={tryOut.onClick}
            style={{
              flexShrink: 0,
              fontSize: '0.78rem',
              padding: '0.25rem 0.5rem',
              borderColor: 'color-mix(in srgb, var(--le-ok, #7d7) 45%, transparent)',
              color: 'var(--le-ok, #7d7)',
            }}
            title="Quick in-page chat to verify this source"
          >
            Try out
          </button>
        ) : set ? (
          <span
            title={
              lastOk
                ? `API key configured · successful chat: ${lastOk}`
                : 'API key configured (settings file and/or environment)'
            }
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '1.35rem',
              height: '1.35rem',
              borderRadius: '4px',
              border: '1px solid color-mix(in srgb, var(--le-ok, #7d7) 55%, transparent)',
              background: 'color-mix(in srgb, var(--le-ok, #7d7) 12%, transparent)',
              color: 'var(--le-ok, #7d7)',
              fontSize: '0.95rem',
              lineHeight: 1,
              flexShrink: 0,
            }}
            aria-label={
              lastOk
                ? `API key configured; chat used successfully ${lastOk}`
                : 'API key configured for this provider'
            }
          >
            ✓
          </span>
        ) : null}
      </div>
      <p id={`hint-${fieldKey}`} className="forge-support" style={{ fontSize: '0.78rem', margin: '0.2rem 0 0', opacity: 0.92 }}>
        {set ? sourceHint : <>No API key in the settings file or matching environment variables for this provider.</>}
      </p>
    </div>
  )
}
