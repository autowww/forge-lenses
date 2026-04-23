import { Link } from 'react-router-dom'
import { STUDIO_VOCAB, type AdvancedSurfaceFrame } from '../../nav/studioVisibleCopy'

export function AdvancedSurfaceFraming({
  frame,
  className = '',
}: {
  frame: AdvancedSurfaceFrame
  /** Optional wrapper classes (e.g. dark lab pages). */
  className?: string
}) {
  return (
    <section
      className={`le-advanced-surface-frame forge-support${className ? ` ${className}` : ''}`}
      aria-label="Advanced surface: audience, impact, and how to return"
    >
      <ul
        className="le-list le-advanced-surface-frame__list"
        style={{ fontSize: '0.88rem', lineHeight: 1.55, margin: '0 0 0.75rem', paddingLeft: '1.2rem' }}
      >
        <li>
          <strong>Who this is for:</strong> {frame.audience}
        </li>
        <li>
          <strong>What it affects:</strong> {frame.affects}
        </li>
        <li>
          <strong>When to use it:</strong> {frame.whenToUse}
        </li>
        <li>
          <strong>Safety:</strong> {frame.safety}
        </li>
      </ul>
      <p style={{ fontSize: '0.88rem', margin: 0 }}>
        <strong>Where to go next:</strong>{' '}
        <Link to={frame.returnTo}>{frame.returnLabel}</Link>
        {' · '}
        Day-to-day delivery: <Link to="/plan?tab=today">{STUDIO_VOCAB.today}</Link>,{' '}
        <Link to="/board">{STUDIO_VOCAB.boards}</Link>,{' '}
        <Link to="/projects">{STUDIO_VOCAB.projects}</Link>. Other inspect tools stay under{' '}
        <strong>Settings (gear)</strong> → {STUDIO_VOCAB.adminInspect}.
      </p>
    </section>
  )
}
