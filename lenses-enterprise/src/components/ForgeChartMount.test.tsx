import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ForgeChartMount } from './ForgeChartMount'

describe('ForgeChartMount', () => {
  it('renders title and chart mount attributes for ForgeDataCharts', () => {
    window.ForgeDataCharts = { mountAll: vi.fn() }
    render(
      <ForgeChartMount
        title="Test chart"
        chartKind="commit_daily"
        dataUrl="/api/chart-data/overview"
      />,
    )
    expect(screen.getByText('Test chart')).toBeInTheDocument()
    const mount = document.querySelector('[data-ks-chart-kind="commit_daily"]')
    expect(mount).toBeTruthy()
    expect(mount?.getAttribute('data-ks-chart-url')).toBe('/api/chart-data/overview')
  })
})
