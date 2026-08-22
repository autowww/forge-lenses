import { studioBuildDetails, studioBuildFooterLine } from '../util/studioBuildInfo'

type Props = {
  hidden: boolean
}

/** Lightweight splash for Virtual Camera Studio Electron — not full Forge Lenses workspace scan. */
export function VirtualCameraSplash({ hidden }: Props) {
  return (
    <div className="le-splash le-splash--virtual-camera" hidden={hidden} aria-busy={!hidden}>
      <div className="le-splash__panel">
        <h1 className="le-splash__logo le-splash__logo--virtual-camera">Virtual Camera Studio</h1>
        <div className="le-splash__spinner" aria-hidden />
        <h2 className="le-splash__title">Starting Virtual Camera Studio…</h2>
        <p className="le-splash__detail">Connecting to the local camera server on this machine.</p>
        <p className="le-splash__hint">Virtual webcam profiles for VDI and conferencing — not Forge Lenses Studio.</p>
        <details className="le-splash__technical le-splash__build-inspect">
          <summary>Build details (inspect)</summary>
          <p className="le-splash__build">{studioBuildFooterLine()}</p>
          <pre className="le-splash__technical-pre">{studioBuildDetails()}</pre>
        </details>
      </div>
    </div>
  )
}
