import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { GapsSummary } from './GapsSummary';
import type { ResearchResult } from '@/lib/parseResearch';

const researchWithGaps: ResearchResult = {
  strategic_initiatives: { found: true, content: 'Some strategic data' },
  competitive_landscape: { found: false, reason: 'No public information available' },
  news_momentum: { found: true, content: 'Recent funding round' },
  industry_context: { found: false, reason: 'Research timed out' },
  culture_values: { found: true, content: 'Innovation culture' },
  leadership_direction: { found: true, content: 'CEO is focused on AI' },
  synthesis: 'Company overview',
  gaps: ['competitive_landscape', 'industry_context'],
  completed_at: '2026-02-09T12:00:00Z',
};

describe('GapsSummary', () => {
  it('renders nothing when there are no gaps', () => {
    const { container } = render(
      <GapsSummary
        gaps={[]}
        research={{ ...researchWithGaps, gaps: [] }}
        totalSources={6}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it('shows gap count and total sources', () => {
    render(
      <GapsSummary
        gaps={['competitive_landscape', 'industry_context']}
        research={researchWithGaps}
        totalSources={6}
      />,
    );
    expect(
      screen.getByText(/2 of 6 research categories with incomplete context/),
    ).toBeInTheDocument();
  });

  it('lists each gap with its category label', () => {
    render(
      <GapsSummary
        gaps={['competitive_landscape', 'industry_context']}
        research={researchWithGaps}
        totalSources={6}
      />,
    );
    expect(screen.getByText('Competitive Landscape:')).toBeInTheDocument();
    expect(screen.getByText('Industry Context:')).toBeInTheDocument();
  });

  it('shows gap reason from research data', () => {
    render(
      <GapsSummary
        gaps={['competitive_landscape']}
        research={researchWithGaps}
        totalSources={6}
      />,
    );
    expect(
      screen.getByText(/No public information available/),
    ).toBeInTheDocument();
  });

  it('shows non-blocking info message', () => {
    render(
      <GapsSummary
        gaps={['industry_context']}
        research={researchWithGaps}
        totalSources={6}
      />,
    );
    expect(
      screen.getByText("This won't block your application"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        /Document generation will proceed with available information/,
      ),
    ).toBeInTheDocument();
  });

  it('renders Add Manual Context button when onAddContext provided', async () => {
    const user = userEvent.setup();
    const handleAddContext = vi.fn();
    render(
      <GapsSummary
        gaps={['industry_context']}
        research={researchWithGaps}
        totalSources={6}
        onAddContext={handleAddContext}
      />,
    );
    const button = screen.getByRole('button', { name: /add manual context/i });
    expect(button).toBeInTheDocument();
    await user.click(button);
    expect(handleAddContext).toHaveBeenCalledOnce();
  });

  it('does not render Add Manual Context button when onAddContext not provided', () => {
    render(
      <GapsSummary
        gaps={['industry_context']}
        research={researchWithGaps}
        totalSources={6}
      />,
    );
    expect(
      screen.queryByRole('button', { name: /add manual context/i }),
    ).not.toBeInTheDocument();
  });

  it('shows suggestion text for known categories', () => {
    render(
      <GapsSummary
        gaps={['news_momentum']}
        research={{
          ...researchWithGaps,
          news_momentum: { found: false, reason: 'Not found' },
          gaps: ['news_momentum'],
        }}
        totalSources={6}
      />,
    );
    expect(
      screen.getByText(/press releases, funding announcements/),
    ).toBeInTheDocument();
  });
});
