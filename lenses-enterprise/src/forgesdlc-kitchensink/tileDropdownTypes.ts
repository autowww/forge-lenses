import type { ReactNode } from 'react'

/** Visual tone for optional status chip on a tile. */
export type TileDropdownStatusVariant = 'default' | 'good' | 'warn' | 'bad'

/** Supplemental label/value rows (e.g. size, fingerprint, tier). */
export type TileDropdownMetaRow = {
  label: string
  value: string
}

export type TileDropdownOption = {
  value: string
  /** Primary heading in the tile and trigger summary. */
  title: string
  /** One line under the title in the panel (and optional second line in trigger). */
  subtitle?: string
  /** Longer body copy in the panel only. */
  description?: string
  meta?: TileDropdownMetaRow[]
  status?: {
    text: string
    variant?: TileDropdownStatusVariant
  }
  disabled?: boolean
}

export type TileRenderContext = {
  selected: boolean
  highlighted: boolean
}

export type TileDropdownRenderTile = (
  option: TileDropdownOption,
  ctx: TileRenderContext,
) => ReactNode
