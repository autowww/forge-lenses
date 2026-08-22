import type { ReactNode } from 'react'

export type ForgeKeyValueItem = {
  label: string
  value: ReactNode
  title?: string
}

export type ForgeKeyValueGridProps = {
  items: ForgeKeyValueItem[]
  className?: string
  /** Visually compact rows (default true for run metadata). */
  dense?: boolean
  'aria-label'?: string
}

/**
 * Dense metadata grid for IDs, owners, timestamps, policy hints — uses design tokens from `forge-react-primitives.css`.
 */
export function ForgeKeyValueGrid({
  items,
  className = '',
  dense = true,
  'aria-label': ariaLabel = 'Metadata',
}: ForgeKeyValueGridProps) {
  if (!items.length) return null
  return (
    <dl
      className={`ks-fe-kvgrid${dense ? ' ks-fe-kvgrid--dense' : ''} ${className}`.trim()}
      aria-label={ariaLabel}
    >
      {items.map((row, i) => (
        <div className="ks-fe-kvgrid__row" key={`${row.label}-${i}`}>
          <dt className="ks-fe-kvgrid__label">{row.label}</dt>
          <dd className="ks-fe-kvgrid__value" title={row.title}>
            {row.value}
          </dd>
        </div>
      ))}
    </dl>
  )
}
