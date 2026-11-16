import type { ReactNode } from 'react'

type RoadmapSectionPreviewProps = {
  title: string
  bodyLines: string[]
  sectionId: string
}

export function RoadmapSectionPreview({ title, bodyLines, sectionId }: RoadmapSectionPreviewProps) {
  const items: ReactNode[] = []
  let listBuffer: string[] = []

  function flushList() {
    if (!listBuffer.length) return
    const captured = [...listBuffer]
    listBuffer = []
    items.push(
      <ul key={`ul-${items.length}`}>
        {captured.map((line, i) => (
          <li key={i}>{line}</li>
        ))}
      </ul>,
    )
  }

  for (const raw of bodyLines) {
    const line = raw.trimEnd()
    if (!line.trim()) {
      flushList()
      continue
    }
    if (line.startsWith('## ')) {
      flushList()
      items.push(
        <h3 key={`h3-${items.length}`}>{line.slice(3).trim()}</h3>,
      )
      continue
    }
    if (line.startsWith('### ')) {
      flushList()
      items.push(
        <h4 key={`h4-${items.length}`}>{line.slice(4).trim()}</h4>,
      )
      continue
    }
    if (line.startsWith('- ') || line.startsWith('* ')) {
      listBuffer.push(line.slice(2).trim())
      continue
    }
    flushList()
    items.push(<p key={`p-${items.length}`}>{line}</p>)
  }
  flushList()

  return (
    <article className="lenses-roadmap-preview-doc md-prose" data-section-id={sectionId}>
      {title ? <h2>{title}</h2> : null}
      {items.length ? items : <p className="forge-support">This section has no body content.</p>}
    </article>
  )
}
