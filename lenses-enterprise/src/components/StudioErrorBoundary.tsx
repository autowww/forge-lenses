import { Component, type ErrorInfo, type ReactNode } from 'react'

type Props = { children: ReactNode }

type State = { error: Error | null }

/**
 * Catches render/lifecycle errors so a failed route or provider does not leave a silent blank viewport.
 */
export class StudioErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('Lenses Studio render error:', error.message, info.componentStack)
  }

  render(): ReactNode {
    if (this.state.error) {
      return (
        <div
          className="le-root"
          style={{
            padding: 'clamp(1.25rem, 4vw, 2.5rem)',
            maxWidth: '40rem',
            margin: '0 auto',
          }}
        >
          <h1 className="le-h1">Something broke in this view</h1>
          <p className="forge-support" style={{ marginTop: '0.75rem' }}>
            Studio hit an unexpected rendering problem. Reloading usually restores the shell; if it repeats, note
            what you clicked last.
          </p>
          <details className="forge-support" style={{ marginTop: '0.75rem', fontSize: '0.85rem' }}>
            <summary style={{ cursor: 'pointer' }}>Show technical details</summary>
            <pre
              className="le-preview"
              style={{
                marginTop: '0.45rem',
                fontSize: '0.78rem',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
              }}
            >
              {this.state.error.message}
            </pre>
          </details>
          <p className="forge-support" style={{ marginTop: '0.5rem', fontSize: '0.82rem' }}>
            The browser console lists the component stack for engineers.
          </p>
          <button
            type="button"
            className="le-btn le-btn--primary"
            style={{ marginTop: '1rem' }}
            onClick={() => window.location.reload()}
          >
            Reload page
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
