import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ResourceFetchStatus } from './ResourceFetchStatus'

describe('ResourceFetchStatus', () => {
  it('renders hard failure with retry', () => {
    const onRetry = vi.fn()
    render(
      <ResourceFetchStatus
        resourceLabel="board registry"
        isFetching={false}
        hasDisplayPayload={false}
        isHydrating={false}
        lastError="HTTP 503"
        servingFromCacheAfterFailure={false}
        snapshotAtLabel={null}
        onRetry={onRetry}
      />,
    )
    expect(screen.getByRole('heading', { name: /couldn’t load this boards list/i })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /retry/i }))
    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  it('renders stale banner when serving cache after failure', () => {
    render(
      <ResourceFetchStatus
        resourceLabel="board registry"
        isFetching={false}
        hasDisplayPayload
        isHydrating={false}
        lastError="network"
        servingFromCacheAfterFailure
        snapshotAtLabel="Apr 1, 2026, 3:00 PM"
        onRetry={vi.fn()}
      />,
    )
    expect(screen.getByRole('heading', { name: /showing last saved boards list/i })).toBeInTheDocument()
    expect(screen.getByText(/Apr 1, 2026/)).toBeInTheDocument()
  })

  it('renders nothing when live and idle', () => {
    const { container } = render(
      <ResourceFetchStatus
        resourceLabel="board registry"
        isFetching={false}
        hasDisplayPayload
        isHydrating={false}
        lastError={null}
        servingFromCacheAfterFailure={false}
        snapshotAtLabel="now"
        onRetry={vi.fn()}
      />,
    )
    expect(container.firstChild).toBeNull()
  })
})
