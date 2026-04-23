import type { CSSProperties, ReactNode } from 'react'

type Props = {
  inputId: string
  listId: string
  label: ReactNode
  /** Shown under the field (e.g. loading / catalog error). */
  hint?: string | null
  value: string
  onChange: (next: string) => void
  optionIds: string[]
  disabled?: boolean
  /** When true, input shows busy state for catalog fetch. */
  catalogBusy?: boolean
  className?: string
  style?: CSSProperties
}

/**
 * Editable model id control: pick from suggestions or type any id. Empty value means “use routing / server default”.
 */
export function ModelIdComboboxField({
  inputId,
  listId,
  label,
  hint,
  value,
  onChange,
  optionIds,
  disabled,
  catalogBusy,
  className,
  style,
}: Props) {
  return (
    <div className={className} style={style}>
      <label className="forge-support" style={{ display: 'block', fontSize: '0.8rem', margin: 0 }} htmlFor={inputId}>
        {label}
      </label>
      {hint ? (
        <p className="forge-support" style={{ fontSize: '0.72rem', margin: '0.15rem 0 0.25rem', opacity: 0.78 }}>
          {hint}
        </p>
      ) : null}
      <input
        id={inputId}
        type="text"
        className="le-input le-mono"
        style={{ display: 'block', width: '100%', marginTop: hint ? 0 : '0.2rem' }}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        aria-busy={catalogBusy || undefined}
        autoComplete="off"
        spellCheck={false}
        list={listId}
        title="Pick a suggested id or type your own. Leave empty for the default model."
      />
      <datalist id={listId}>
        {optionIds.map((mid) => (
          <option key={mid} value={mid} />
        ))}
      </datalist>
    </div>
  )
}
