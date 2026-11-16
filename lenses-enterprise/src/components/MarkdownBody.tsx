import type { AnchorHTMLAttributes } from 'react'
import { Link } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  isProbablyExternalHttpUrl,
  markdownHrefToStudioTo,
} from '../util/markdownStudioLink'

type Props = {
  text: string
  className?: string
}

type MdAnchorProps = AnchorHTMLAttributes<HTMLAnchorElement>

/**
 * Root-relative and same-origin absolute links stay in the Studio SPA. Plain `/plan?…`
 * would otherwise leave `/studio/…` and load Classic in the top window (often a broken
 * or blank-looking view).
 */
function MarkdownAnchor(props: MdAnchorProps) {
  const { href, children, ...rest } = props
  const raw = href ?? ''
  const studioTo = markdownHrefToStudioTo(raw)

  if (studioTo != null) {
    return (
      <Link to={studioTo} {...rest}>
        {children}
      </Link>
    )
  }

  if (isProbablyExternalHttpUrl(raw)) {
    return (
      <a href={raw} target="_blank" rel="noreferrer" {...rest}>
        {children}
      </a>
    )
  }

  return <a {...props} />
}

/** Renders GitHub-flavored Markdown with KS-friendly class wrapper. */
export function MarkdownBody({ text, className = '' }: Props) {
  return (
    <div className={`md-prose ${className}`.trim()}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={{ a: MarkdownAnchor }}>
        {text}
      </ReactMarkdown>
    </div>
  )
}
