import { useState } from 'react'
import setupScript from '../assets/setup-ollama-for-lenses.sh?raw'

const RUN_FROM_REPO = `cd /path/to/forge-lenses   # your clone
bash scripts/setup-ollama-for-lenses.sh

# Or from a downloaded copy (no sudo — run as your user):
#   OLLAMA_AUTO_INSTALL=1 bash ./setup-ollama-for-lenses.sh`

export function OllamaSetupScriptPanel() {
  const [copied, setCopied] = useState<'script' | 'run' | null>(null)

  async function copy(text: string, kind: 'script' | 'run') {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(kind)
      window.setTimeout(() => setCopied(null), 2000)
    } catch {
      setCopied(null)
    }
  }

  return (
    <details
      className="forge-support"
      style={{
        marginTop: '0.65rem',
        padding: '0.5rem 0.65rem',
        borderRadius: '6px',
        border: '1px solid var(--le-border, rgba(255,255,255,0.12))',
        background: 'color-mix(in srgb, var(--le-panel, #1a1a1f) 88%, transparent)',
      }}
    >
      <summary style={{ cursor: 'pointer', fontWeight: 600 }}>
        Setup script (install / start Ollama / pull model)
      </summary>
      <p style={{ fontSize: '0.85rem', margin: '0.65rem 0 0.5rem', opacity: 0.92 }}>
        Bundled in this repo as <code className="le-mono">scripts/setup-ollama-for-lenses.sh</code>. Run in a
        terminal (install step may ask for sudo). Or copy the script below and save it as{' '}
        <code className="le-mono">setup-ollama-for-lenses.sh</code>, then{' '}
        <code className="le-mono">chmod +x</code> and run it.
      </p>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.5rem' }}>
        <button type="button" className="le-btn le-btn--primary" onClick={() => copy(setupScript, 'script')}>
          {copied === 'script' ? 'Copied' : 'Copy script'}
        </button>
        <button type="button" className="le-btn" onClick={() => copy(RUN_FROM_REPO, 'run')}>
          {copied === 'run' ? 'Copied' : 'Copy repo command'}
        </button>
        <a
          className="le-btn"
          href={`${import.meta.env.BASE_URL}snippets/setup-ollama-for-lenses.sh`}
          download="setup-ollama-for-lenses.sh"
          style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center' }}
        >
          Download .sh
        </a>
      </div>
      <pre
        className="forge-support le-mono"
        style={{
          fontSize: '0.72rem',
          margin: 0,
          padding: '0.6rem',
          overflow: 'auto',
          maxHeight: '14rem',
          borderRadius: '4px',
          background: 'rgba(0,0,0,0.35)',
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
        }}
      >
        {setupScript.trimEnd()}
      </pre>
    </details>
  )
}
