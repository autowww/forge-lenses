import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { SyncDraftPreviewDialog } from './SyncDraftPreviewDialog'

describe('SyncDraftPreviewDialog', () => {
  it('calls onCancel when Escape is pressed and not busy', () => {
    const onCancel = vi.fn()
    render(
      <SyncDraftPreviewDialog
        open
        currentMarkdown="old"
        nextMarkdown="new"
        onCancel={onCancel}
        onConfirm={vi.fn()}
        confirmBusy={false}
      />,
    )
    fireEvent.keyDown(document, { key: 'Escape', bubbles: true })
    expect(onCancel).toHaveBeenCalledTimes(1)
  })

  it('does not call onCancel on Escape while busy', () => {
    const onCancel = vi.fn()
    render(
      <SyncDraftPreviewDialog
        open
        currentMarkdown="old"
        nextMarkdown="new"
        onCancel={onCancel}
        onConfirm={vi.fn()}
        confirmBusy
      />,
    )
    fireEvent.keyDown(document, { key: 'Escape', bubbles: true })
    expect(onCancel).not.toHaveBeenCalled()
  })

  it('exposes aria-labelledby and aria-describedby for the dialog', () => {
    render(
      <SyncDraftPreviewDialog
        open
        currentMarkdown="a"
        nextMarkdown="b"
        onCancel={vi.fn()}
        onConfirm={vi.fn()}
        confirmBusy={false}
      />,
    )
    const dialog = screen.getByRole('dialog', { name: /Replace Foundation Brief Markdown/i })
    const labelledBy = dialog.getAttribute('aria-labelledby')
    const describedBy = dialog.getAttribute('aria-describedby')
    expect(labelledBy).toBeTruthy()
    expect(describedBy).toBeTruthy()
    if (labelledBy) expect(document.getElementById(labelledBy)).toBeTruthy()
    if (describedBy) expect(document.getElementById(describedBy)).toBeTruthy()
  })
})
