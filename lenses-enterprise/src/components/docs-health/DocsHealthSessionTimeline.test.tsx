import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { DocsHealthSessionTimeline } from './DocsHealthSessionTimeline'

describe('DocsHealthSessionTimeline', () => {
  it('renders typed blocks distinctly', () => {
    render(
      <MemoryRouter>
        <DocsHealthSessionTimeline
          sessionStatus="running"
          events={[
            { type: 'summary', title: 'Context', body: 'Hello world', ts: '2020-01-01T00:00:00Z' },
            { type: 'question', prompt: 'Choose next action?', ts: '2020-01-01T00:01:00Z' },
            { type: 'token_stats', last_model: 'gpt-test', snapshot: { prompt_tokens: 1, completion_tokens: 2 }, ts: '2020-01-01T00:02:00Z' },
          ]}
        />
      </MemoryRouter>,
    )
    expect(screen.getByText('Context')).toBeInTheDocument()
    expect(screen.getByText('Hello world')).toBeInTheDocument()
    expect(screen.getByText('Choose next action?')).toBeInTheDocument()
    expect(screen.getByText(/gpt-test/)).toBeInTheDocument()
    expect(screen.getByText(/in 1/)).toBeInTheDocument()
  })

  it('hides token_stats when omitEventTypes includes token_stats', () => {
    render(
      <MemoryRouter>
        <DocsHealthSessionTimeline
          sessionStatus="running"
          omitEventTypes={['token_stats']}
          events={[
            { type: 'summary', title: 'Context', body: 'Hello', ts: '2020-01-01T00:00:00Z' },
            { type: 'token_stats', last_model: 'hidden-model', snapshot: { prompt_tokens: 1 }, ts: '2020-01-01T00:01:00Z' },
          ]}
        />
      </MemoryRouter>,
    )
    expect(screen.getByText('Context')).toBeInTheDocument()
    expect(screen.queryByText(/hidden-model/)).not.toBeInTheDocument()
  })

  it('shows empty hint when no events', () => {
    render(
      <MemoryRouter>
        <DocsHealthSessionTimeline sessionStatus="running" events={[]} />
      </MemoryRouter>,
    )
    expect(screen.getByText(/Waiting for the next events from this run/i)).toBeInTheDocument()
  })
})
