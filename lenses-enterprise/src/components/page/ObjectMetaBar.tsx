import type { ReactNode } from 'react'

export type ObjectMetaItem = {
  label: string
  value: ReactNode
}

type ObjectMetaBarProps = {
  items: ObjectMetaItem[]
  /** Accessible name for the strip. */
  label?: string
  className?: string
}

/**
 * Compact metadata strip (identity, status, timestamps) under a page header.
 */
export function ObjectMetaBar({
  items,
  label = 'Object details',
  className = '',
}: ObjectMetaBarProps) {
  if (items.length === 0) return null
  return (
    <div className={`le-object-meta-bar${className ? ` ${className}` : ''}`} role="group" aria-label={label}>
      <ul className="le-object-meta-bar__list">
        {items.map((it) => (
          <li key={it.label} className="le-object-meta-bar__item">
            <span className="le-object-meta-bar__label">{it.label}</span>
            <span className="le-object-meta-bar__value">{it.value}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
