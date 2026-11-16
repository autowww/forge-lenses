import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties } from 'react'
import { useSearchParams } from 'react-router-dom'
import { apiGetJson, qs } from '../../api/http'

export type NestedRoadmapColumn = { id: string; label: string }
export type NestedRoadmapTrack = { id: string; label: string }
export type NestedRoadmapBar = {
  id: string
  label: string
  trackId: string
  startColumnId: string
  endColumnId: string
  summary?: string
  child?: NestedRoadmapLevel
}
export type NestedRoadmapLevel = {
  version: number
  title: string
  columns: NestedRoadmapColumn[]
  tracks: NestedRoadmapTrack[]
  bars: NestedRoadmapBar[]
}

type NestedRoadmapPayload = {
  ok?: boolean
  config?: NestedRoadmapLevel
  error?: string
}

const TONE_CLASSES = ['cyan', 'emerald', 'amber', 'violet'] as const

function hashTone(id: string, index: number): string {
  let h = 0
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) | 0
  return TONE_CLASSES[(Math.abs(h) + index) % TONE_CLASSES.length]
}

function columnIndexMap(level: NestedRoadmapLevel): Map<string, number> {
  const m = new Map<string, number>()
  level.columns.forEach((c, i) => m.set(c.id, i))
  return m
}

function barGridColumn(level: NestedRoadmapLevel, bar: NestedRoadmapBar): string {
  const cmap = columnIndexMap(level)
  const s = cmap.get(bar.startColumnId)
  const e = cmap.get(bar.endColumnId)
  if (s == null || e == null || s > e) return '1 / 2'
  return `${s + 1} / ${e + 2}`
}

function columnLabel(level: NestedRoadmapLevel, id: string): string {
  return level.columns.find((c) => c.id === id)?.label ?? id
}

function hasDrillChild(bar: NestedRoadmapBar): boolean {
  return Boolean(bar.child?.bars?.length)
}

type NestedRoadmapGridProps = {
  level: NestedRoadmapLevel
  mini?: boolean
  onDrill?: (bar: NestedRoadmapBar) => void
  onSelectLeaf?: (bar: NestedRoadmapBar) => void
  selectedBarId?: string | null
  modalOpenForBarId?: string | null
}

function NestedRoadmapGrid({
  level,
  mini = false,
  onDrill,
  onSelectLeaf,
  selectedBarId,
  modalOpenForBarId,
}: NestedRoadmapGridProps) {
  const barsByTrack = useMemo(() => {
    const m = new Map<string, NestedRoadmapBar[]>()
    for (const bar of level.bars) {
      const tid = bar.trackId || ''
      const list = m.get(tid) ?? []
      list.push(bar)
      m.set(tid, list)
    }
    return m
  }, [level.bars])

  return (
    <div
      className={`le-nested-roadmap__grid${mini ? ' le-nested-roadmap__grid--mini' : ''}`}
      data-ks-type="nested-roadmap-grid"
      style={{ '--le-nrm-cols': level.columns.length } as CSSProperties}
    >
      <div className="le-nested-roadmap__corner" aria-hidden />
      {level.columns.map((col) => (
        <div key={col.id} className="le-nested-roadmap__col-head">
          {col.label}
        </div>
      ))}
      {level.tracks.map((track) => (
        <div key={track.id} className="le-nested-roadmap__track-row">
          <div className="le-nested-roadmap__track-label">{track.label}</div>
          <div className="le-nested-roadmap__lane">
            {(barsByTrack.get(track.id) ?? []).map((bar, ri) => {
              const tone = hashTone(bar.id, ri)
              const drill = hasDrillChild(bar)
              const gridColumn = barGridColumn(level, bar)
              const selected = selectedBarId === bar.id
              if (drill && onDrill) {
                const modalOpen = modalOpenForBarId === bar.id
                return (
                  <button
                    key={bar.id}
                    type="button"
                    className={`le-nested-roadmap__bar le-nested-roadmap__bar--drill le-nested-roadmap__bar--${tone}${selected ? ' le-nested-roadmap__bar--selected' : ''}`}
                    style={{ gridColumn }}
                    onClick={() => onDrill(bar)}
                    aria-haspopup="dialog"
                    aria-expanded={modalOpen}
                    title={bar.summary || bar.label}
                    data-ks-type="nested-roadmap-bar"
                  >
                    <span className="le-nested-roadmap__bar-label">{bar.label}</span>
                    <span className="le-nested-roadmap__bar-nest" aria-hidden />
                  </button>
                )
              }
              return (
                <button
                  key={bar.id}
                  type="button"
                  className={`le-nested-roadmap__bar le-nested-roadmap__bar--leaf le-nested-roadmap__bar--${tone}${selected ? ' le-nested-roadmap__bar--selected' : ''}`}
                  style={{ gridColumn }}
                  title={bar.summary || bar.label}
                  aria-pressed={selected}
                  data-ks-type="nested-roadmap-bar"
                  onClick={() => onSelectLeaf?.(bar)}
                >
                  <span className="le-nested-roadmap__bar-label">{bar.label}</span>
                </button>
              )
            })}
          </div>
        </div>
      ))}
    </div>
  )
}

type Props = {
  frameTitle?: string
  frameMinHeight?: string
}

export function NestedRoadmapHorizon({
  frameTitle = 'Roadmap horizon',
  frameMinHeight = 'min(52vh, 28rem)',
}: Props) {
  const [sp] = useSearchParams()
  const repo = sp.get('repo')?.trim() ?? ''
  const roadmapP = sp.get('roadmap_p')?.trim() ?? sp.get('p')?.trim() ?? ''
  const [root, setRoot] = useState<NestedRoadmapLevel | null>(null)
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState<string | null>(null)
  const [trail, setTrail] = useState<{ label: string; level: NestedRoadmapLevel }[]>([])
  const [modalLevel, setModalLevel] = useState<NestedRoadmapLevel | null>(null)
  const [modalTitle, setModalTitle] = useState('')
  const [modalSourceBarId, setModalSourceBarId] = useState<string | null>(null)
  const [detailBar, setDetailBar] = useState<NestedRoadmapBar | null>(null)
  const [modalVisible, setModalVisible] = useState(false)
  const closeBtnRef = useRef<HTMLButtonElement>(null)
  const modalRef = useRef<HTMLDivElement>(null)

  const load = useCallback(() => {
    setLoading(true)
    setErr(null)
    const q = qs({
      repo: repo || undefined,
      roadmap_p: roadmapP || undefined,
    })
    apiGetJson<NestedRoadmapPayload>(`/api/nested-roadmap-config${q}`)
      .then((r) => {
        if (r.ok && r.config) {
          setRoot(r.config)
          setTrail([])
          setDetailBar(null)
        } else {
          setRoot(null)
          setErr(r.error || 'nested_roadmap_unavailable')
        }
      })
      .catch((e) => {
        setRoot(null)
        setErr(e instanceof Error ? e.message : 'Load failed')
      })
      .finally(() => setLoading(false))
  }, [repo, roadmapP])

  useEffect(() => {
    load()
  }, [load])

  const activeLevel = trail.length ? trail[trail.length - 1].level : root

  const closeModal = useCallback(() => {
    setModalVisible(false)
    window.setTimeout(() => {
      setModalLevel(null)
      setModalTitle('')
      setModalSourceBarId(null)
    }, 220)
  }, [])

  function openDrill(bar: NestedRoadmapBar) {
    if (!bar.child) return
    setModalTitle(bar.label)
    setModalLevel(bar.child)
    setModalSourceBarId(bar.id)
    setModalVisible(true)
  }

  function pushTrail(bar: NestedRoadmapBar) {
    if (!bar.child) return
    setTrail((prev) => [...prev, { label: bar.label, level: bar.child! }])
    setDetailBar(null)
  }

  useEffect(() => {
    if (!modalLevel) return
    const id = window.requestAnimationFrame(() => setModalVisible(true))
    return () => window.cancelAnimationFrame(id)
  }, [modalLevel])

  useEffect(() => {
    if (!modalVisible) return
    closeBtnRef.current?.focus()
    function onKey(ev: KeyboardEvent) {
      if (ev.key === 'Escape') {
        ev.preventDefault()
        closeModal()
      }
      if (ev.key === 'Tab' && modalRef.current) {
        const focusable = modalRef.current.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
        )
        if (!focusable.length) return
        const first = focusable[0]
        const last = focusable[focusable.length - 1]
        if (ev.shiftKey && document.activeElement === first) {
          ev.preventDefault()
          last.focus()
        } else if (!ev.shiftKey && document.activeElement === last) {
          ev.preventDefault()
          first.focus()
        }
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [modalVisible, closeModal])

  return (
    <section
      className="le-nested-roadmap"
      aria-label={frameTitle}
      style={{ minHeight: frameMinHeight }}
      data-ks-type="nested-roadmap-horizon"
    >
      <header className="le-nested-roadmap__header">
        <h3 className="le-nested-roadmap__title">{activeLevel?.title ?? frameTitle}</h3>
        {trail.length ? (
          <nav className="le-nested-roadmap__breadcrumb" aria-label="Roadmap drill-down trail">
            <button type="button" className="le-nested-roadmap__bc-btn" onClick={() => setTrail([])}>
              {root?.title ?? 'Root'}
            </button>
            {trail.map((t, i) => (
              <span key={`${t.label}-${i}`}>
                <span className="le-nested-roadmap__bc-sep" aria-hidden>
                  ›
                </span>
                {i < trail.length - 1 ? (
                  <button
                    type="button"
                    className="le-nested-roadmap__bc-btn"
                    onClick={() => setTrail(trail.slice(0, i + 1))}
                  >
                    {t.label}
                  </button>
                ) : (
                  <span className="le-nested-roadmap__bc-current">{t.label}</span>
                )}
              </span>
            ))}
          </nav>
        ) : null}
      </header>
      {loading ? <p className="forge-support">Loading roadmap horizon…</p> : null}
      {err ? <p className="le-danger">{err}</p> : null}
      {activeLevel && !loading ? (
        <>
          <NestedRoadmapGrid
            level={activeLevel}
            selectedBarId={detailBar?.id ?? null}
            modalOpenForBarId={modalSourceBarId}
            onSelectLeaf={(bar) => setDetailBar((prev) => (prev?.id === bar.id ? null : bar))}
            onDrill={(bar) => {
              if (bar.child?.bars && bar.child.bars.length > 4) {
                openDrill(bar)
              } else {
                pushTrail(bar)
              }
            }}
          />
          {detailBar ? (
            <aside
              className="le-nested-roadmap__tier-detail"
              aria-label="Roadmap tier detail"
              data-ks-type="nested-roadmap-tier-detail"
            >
              <h4 className="le-nested-roadmap__tier-title">{detailBar.label}</h4>
              {detailBar.summary ? (
                <p className="le-nested-roadmap__tier-summary">{detailBar.summary}</p>
              ) : (
                <p className="le-nested-roadmap__tier-summary le-muted">No summary for this tier.</p>
              )}
              <dl className="le-nested-roadmap__tier-meta">
                <div>
                  <dt>Horizon</dt>
                  <dd>
                    {columnLabel(activeLevel, detailBar.startColumnId)} →{' '}
                    {columnLabel(activeLevel, detailBar.endColumnId)}
                  </dd>
                </div>
                <div>
                  <dt>Track</dt>
                  <dd>{activeLevel.tracks.find((t) => t.id === detailBar.trackId)?.label ?? detailBar.trackId}</dd>
                </div>
              </dl>
              <button type="button" className="le-btn le-btn--ghost" onClick={() => setDetailBar(null)}>
                Dismiss
              </button>
            </aside>
          ) : null}
        </>
      ) : null}
      {modalLevel ? (
        <div
          className={`le-nested-roadmap__modal-backdrop${modalVisible ? ' le-nested-roadmap__modal-backdrop--open' : ''}`}
          role="presentation"
          onClick={(e) => {
            if (e.target === e.currentTarget) closeModal()
          }}
        >
          <div
            ref={modalRef}
            className={`le-nested-roadmap__modal${modalVisible ? ' le-nested-roadmap__modal--open' : ''}`}
            role="dialog"
            aria-modal="true"
            aria-labelledby="le-nrm-modal-title"
            data-ks-type="nested-roadmap-modal"
            onClick={(e) => e.stopPropagation()}
          >
            <header className="le-nested-roadmap__modal-header">
              <h4 id="le-nrm-modal-title">{modalTitle}</h4>
              <button
                ref={closeBtnRef}
                type="button"
                className="le-btn le-btn--ghost"
                onClick={closeModal}
              >
                Close
              </button>
            </header>
            <NestedRoadmapGrid level={modalLevel} mini onDrill={pushTrail} />
          </div>
        </div>
      ) : null}
    </section>
  )
}
