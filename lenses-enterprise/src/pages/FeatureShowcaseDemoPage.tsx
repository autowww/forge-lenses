import { Link } from 'react-router-dom'
import { FeatureShowcase, exampleFeatureShowcaseItems } from '../components/feature-showcase'
import { AdvancedSurfaceFraming } from '../components/page'
import { ADVANCED_SURFACE_FRAMES, STUDIO_VOCAB } from '../nav/studioVisibleCopy'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'

export function FeatureShowcaseDemoPage() {
  useLensesCopilotPage({ route: 'feature-showcase' })
  return (
    <div className="min-h-[80vh] bg-zinc-950 text-zinc-100">
      <header className="mb-2 border-b border-zinc-800/80 px-1 pb-6">
        <p className="mb-3 text-xs uppercase tracking-wide text-zinc-500">
          Lab · not in primary navigation · bookmark OK
        </p>
        <h1 className="text-2xl font-semibold tracking-tight text-zinc-50">Feature showcase</h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-zinc-400">
          Demo of the split scrollytelling layout: scroll the list or click an item — the sticky panel
          updates with layered imagery and light parallax. Resize the window to see the stacked mobile
          layout.
        </p>
        <div className="mt-4 max-w-2xl rounded-md border border-zinc-700/80 bg-zinc-900/60 p-3 text-sm text-zinc-300 [&_a]:text-sky-400 [&_a]:underline-offset-2 hover:[&_a]:underline">
          <AdvancedSurfaceFraming
            className="!text-zinc-300 [&_strong]:text-zinc-200"
            frame={ADVANCED_SURFACE_FRAMES.featureShowcaseLab}
          />
        </div>
        <p className="mt-3 text-sm">
          <Link to="/" className="text-sky-400 underline-offset-2 hover:underline">
            ← {STUDIO_VOCAB.overview}
          </Link>
        </p>
      </header>
      <FeatureShowcase
        items={exampleFeatureShowcaseItems}
        title="Why teams use Lenses Studio"
        className="max-w-6xl px-0 sm:px-0"
      />
    </div>
  )
}
