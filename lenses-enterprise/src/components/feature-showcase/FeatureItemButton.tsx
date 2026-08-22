import type { FeatureShowcaseItem } from './types'

type FeatureItemButtonProps = {
  item: FeatureShowcaseItem
  isActive: boolean
  onActivate: () => void
  visualPanelId: string
}

export function FeatureItemButton({
  item,
  isActive,
  onActivate,
  visualPanelId,
}: FeatureItemButtonProps) {
  return (
    <div
      className={[
        'rounded-2xl border transition-[border-color,box-shadow,background-color] duration-300 ease-out',
        isActive
          ? 'border-amber-400/50 bg-zinc-800/80 shadow-[0_0_0_1px_rgba(251,191,36,0.12),0_16px_40px_-12px_rgba(0,0,0,0.45)]'
          : 'border-zinc-700/80 bg-zinc-900/40 hover:border-zinc-500 hover:bg-zinc-800/50',
      ].join(' ')}
    >
      <button
        type="button"
        aria-pressed={isActive}
        aria-controls={visualPanelId}
        onClick={onActivate}
        className="w-full rounded-2xl px-5 py-4 text-left outline-none focus-visible:ring-2 focus-visible:ring-amber-400/80 focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-950"
      >
        <h3
          className={[
            'text-lg font-semibold tracking-tight transition-colors sm:text-xl',
            isActive ? 'text-amber-100' : 'text-zinc-100',
          ].join(' ')}
        >
          {item.heading}
        </h3>
        <p className="mt-1.5 text-sm leading-relaxed text-zinc-400 sm:text-[0.9375rem]">
          {item.summary}
        </p>
        {item.description ? (
          <p className="mt-3 text-sm leading-relaxed text-zinc-500">{item.description}</p>
        ) : null}
      </button>
      <div className="border-t border-zinc-700/60 px-5 py-3">
        <a
          href={item.cta.href}
          className="inline-flex items-center gap-1.5 text-sm font-medium text-amber-400/95 underline-offset-4 transition-colors hover:text-amber-300 focus-visible:rounded focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-400/90"
          onClick={(e) => e.stopPropagation()}
        >
          {item.cta.label}
          <span aria-hidden className="text-xs opacity-80">
            →
          </span>
        </a>
      </div>
    </div>
  )
}
