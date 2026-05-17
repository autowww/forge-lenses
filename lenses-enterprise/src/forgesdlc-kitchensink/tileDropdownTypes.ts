import type { ReactNode } from 'react'

/** Visual tone for optional status chip on a tile. */
export type TileDropdownStatusVariant = 'default' | 'good' | 'warn' | 'bad'

/** Panel / per-option tile density. Default on the control is `compact`. */
export type TileDropdownDensity = 'compact' | 'hero'

/** Supplemental label/value rows (e.g. size, fingerprint, tier). */
export type TileDropdownMetaRow = {
  label: string
  value: string
}

/**
 * Optional image/icon URL for the default hero renderer.
 * Use `renderTile` for inline SVG or component icons.
 */
export type TileDropdownMedia = {
  kind: 'icon' | 'image'
  src: string
  /** Empty string = decorative (`alt=""`, presentation). */
  alt: string
}

export type TileDropdownOption = {
  value: string
  /** Primary heading in the tile and trigger summary. */
  title: string
  /**
   * Secondary line in **compact** tiles and in the **closed trigger** (with `title`).
   * In **hero** tiles, prefer `lead` for the emphasized line under the title; if `lead`
   * is omitted, `subtitle` is shown in that slot.
   */
  subtitle?: string
  /**
   * Longer body in **compact** tiles (panel only).
   * In **hero** mode, prefer `body`; when `body` is set it wins over `description` for the hero body block.
   */
  description?: string
  /** Overrides per-option density when set; otherwise uses the control `tileDensity`. */
  density?: TileDropdownDensity
  /** Short label above the title (hero). Ignored in compact layout. */
  kicker?: string
  /** Emphasized line under the title in hero tiles; falls back to `subtitle` if unset. */
  lead?: string
  /** Multi-line plain text for hero body; line breaks preserved. Takes precedence over `description` in hero layout. */
  body?: string
  media?: TileDropdownMedia
  /** Closed trigger text when this option is selected (overrides `title` / `subtitle` join). */
  triggerSummary?: string
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
