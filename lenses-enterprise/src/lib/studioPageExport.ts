/** Client-side export of the Studio scrollable main column (not sidebar, header, or Copilot). */

export const STUDIO_EXPORT_ROOT_ID = 'le-studio-export-root' as const

type ScrollSnap = { el: HTMLElement; top: number; left: number }

function collectScrollSnapshots(root: HTMLElement): ScrollSnap[] {
  const snaps: ScrollSnap[] = []
  function visit(el: HTMLElement) {
    const st = getComputedStyle(el)
    const canScrollY =
      (st.overflowY === 'auto' || st.overflowY === 'scroll' || st.overflowY === 'overlay') &&
      el.scrollHeight > el.clientHeight + 1
    const canScrollX =
      (st.overflowX === 'auto' || st.overflowX === 'scroll' || st.overflowX === 'overlay') &&
      el.scrollWidth > el.clientWidth + 1
    if (canScrollY || canScrollX) {
      snaps.push({ el, top: el.scrollTop, left: el.scrollLeft })
    }
    for (let i = 0; i < el.children.length; i++) {
      const c = el.children[i]
      if (c instanceof HTMLElement) visit(c)
    }
  }
  visit(root)
  return snaps
}

function resetScrollSnapshots(snaps: ScrollSnap[]): void {
  for (const s of snaps) {
    s.el.scrollTop = 0
    s.el.scrollLeft = 0
  }
}

function restoreScrollSnapshots(snaps: ScrollSnap[]): void {
  for (let i = snaps.length - 1; i >= 0; i--) {
    const s = snaps[i]
    s.el.scrollTop = s.top
    s.el.scrollLeft = s.left
  }
}

async function withExportScrollReset<T>(root: HTMLElement, fn: () => Promise<T>): Promise<T> {
  const snaps = collectScrollSnapshots(root)
  resetScrollSnapshots(snaps)
  try {
    return await fn()
  } finally {
    restoreScrollSnapshots(snaps)
  }
}

export function slugifyExportBaseName(raw: string): string {
  const collapsed = raw
    .replace(/[<>:"/\\|?*\u0000-\u001f]+/g, '-')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-+|-+$/g, '')
    .trim()
  return collapsed.slice(0, 96) || 'forge-studio-page'
}

function exportBaseNameFromDocumentTitle(): string {
  const t = typeof document !== 'undefined' ? document.title.trim() : ''
  if (!t) return 'forge-studio-page'
  return slugifyExportBaseName(t.replace(/\s*\|\s*/g, '-'))
}

export function getStudioExportRootElement(): HTMLElement | null {
  return document.getElementById(STUDIO_EXPORT_ROOT_ID)
}

function shouldIgnoreExportElement(element: Element): boolean {
  return element instanceof HTMLElement && element.classList.contains('le-evidence-rail')
}

function exportHostDimensions(el: HTMLElement): { w: number; h: number } {
  const w = Math.max(el.scrollWidth, el.clientWidth, el.offsetWidth)
  const h = Math.max(el.scrollHeight, el.clientHeight, el.offsetHeight)
  return { w, h: Math.max(h, 1) }
}

export async function captureStudioMainPageCanvas(): Promise<{
  canvas: HTMLCanvasElement
  baseName: string
}> {
  const el = getStudioExportRootElement()
  if (!el) {
    throw new Error('Studio export region was not found.')
  }
  const html2canvas = (await import('html2canvas')).default
  const { w, h } = exportHostDimensions(el)
  const bg = getComputedStyle(el).backgroundColor

  const canvas = await withExportScrollReset(el, () =>
    html2canvas(el, {
      scale: Math.min(2, Math.max(1, window.devicePixelRatio || 1)),
      useCORS: true,
      allowTaint: false,
      logging: false,
      ignoreElements: shouldIgnoreExportElement,
      backgroundColor: bg && bg !== 'transparent' ? bg : undefined,
      scrollX: 0,
      scrollY: 0,
      windowWidth: w,
      windowHeight: h,
    }),
  )

  return { canvas, baseName: exportBaseNameFromDocumentTitle() }
}

export async function downloadStudioMainPagePng(): Promise<void> {
  const { canvas, baseName } = await captureStudioMainPageCanvas()
  const blob = await new Promise<Blob>((resolve, reject) => {
    canvas.toBlob((b) => (b ? resolve(b) : reject(new Error('Could not encode PNG.'))), 'image/png')
  })
  const url = URL.createObjectURL(blob)
  try {
    const a = document.createElement('a')
    a.href = url
    a.download = `${baseName}.png`
    a.rel = 'noopener'
    a.click()
  } finally {
    URL.revokeObjectURL(url)
  }
}

/**
 * PDF with selectable text (jsPDF `html` + `autoPaging: 'text'`), not a flat screenshot.
 * Charts and other canvas-heavy regions may be simplified compared to PNG export.
 */
export async function downloadStudioMainPagePdf(): Promise<void> {
  const el = getStudioExportRootElement()
  if (!el) {
    throw new Error('Studio export region was not found.')
  }
  const { jsPDF } = await import('jspdf')
  const baseName = exportBaseNameFromDocumentTitle()
  const { w, h } = exportHostDimensions(el)
  const marginPt = 40
  const pdf = new jsPDF({ unit: 'pt', format: 'a4', orientation: 'portrait' })
  const pageW = pdf.internal.pageSize.getWidth()
  const contentW = pageW - 2 * marginPt

  await withExportScrollReset(el, async () => {
    await pdf.html(el, {
      filename: `${baseName}.pdf`,
      margin: marginPt,
      x: marginPt,
      y: marginPt,
      width: contentW,
      windowWidth: w,
      autoPaging: 'text',
      html2canvas: {
        scale: 1,
        useCORS: true,
        allowTaint: true,
        logging: false,
        ignoreElements: shouldIgnoreExportElement,
        backgroundColor: '#ffffff',
        scrollX: 0,
        scrollY: 0,
        windowWidth: w,
        windowHeight: h,
      },
      callback: (doc) => {
        doc.save(`${baseName}.pdf`)
      },
    })
  })
}
