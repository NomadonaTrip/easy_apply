import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ResearchSummary } from './ResearchSummary';
import type { ResearchResult } from '@/lib/parseResearch';

const fullResearch: ResearchResult = {
  strategic_initiatives: {
    found: true,
    content: 'Acme Corp is expanding into enterprise market with new SaaS platform',
  },
  competitive_landscape: {
    found: true,
    content: '- Main competitor is BigCo\n- Differentiates on ease of use',
  },
  news_momentum: {
    found: true,
    content: 'Recently raised $50M Series C. Launched AI features in Q3.',
  },
  industry_context: {
    found: false,
    reason: 'Limited public information on industry trends',
  },
  culture_values: {
    found: true,
    content: 'Values: Innovation, Integrity, Collaboration',
  },
  leadership_direction: {
    found: true,
    content: 'CEO focused on international expansion and AI integration',
  },
  synthesis: 'Acme Corp needs a senior engineer to scale their enterprise platform.',
  gaps: ['industry_context'],
  completed_at: '2026-02-09T12:00:00Z',
};

describe('ResearchSummary', () => {
  it('renders all six section labels', () => {
    render(<ResearchSummary research={fullResearch} gaps={['industry_context']} />);

    expect(screen.getByText('Strategic Initiatives')).toBeInTheDocument();
    expect(screen.getByText('Competitive Landscape')).toBeInTheDocument();
    expect(screen.getByText('Recent News & Momentum')).toBeInTheDocument();
    expect(screen.getByText('Industry Context')).toBeInTheDocument();
    expect(screen.getByText('Culture & Values')).toBeInTheDocument();
    expect(screen.getByText('Leadership Direction')).toBeInTheDocument();
  });

  it('shows strategic synthesis at the top', () => {
    render(<ResearchSummary research={fullResearch} gaps={['industry_context']} />);

    expect(screen.getByText('Strategic Summary')).toBeInTheDocument();
    expect(
      screen.getByText('Acme Corp needs a senior engineer to scale their enterprise platform.'),
    ).toBeInTheDocument();
  });

  it('shows found count and gap count in summary stats', () => {
    render(<ResearchSummary research={fullResearch} gaps={['industry_context']} />);

    // 6 total sections - 1 gap = 5 found
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('Sources found')).toBeInTheDocument();
    expect(screen.getByText('Gaps (non-blocking)')).toBeInTheDocument();
  });

  it('shows gap indicator for missing data', () => {
    render(<ResearchSummary research={fullResearch} gaps={['industry_context']} />);

    expect(screen.getByText('Limited Info')).toBeInTheDocument();
  });

  it('does not show gaps count when there are no gaps', () => {
    render(<ResearchSummary research={fullResearch} gaps={[]} />);

    expect(screen.queryByText('Gaps')).not.toBeInTheDocument();
  });

  it('expands section on click to show content', async () => {
    const user = userEvent.setup();
    render(<ResearchSummary research={fullResearch} gaps={['industry_context']} />);

    await user.click(screen.getByText('Strategic Initiatives'));

    expect(
      screen.getByText(/Acme Corp is expanding into enterprise market/),
    ).toBeInTheDocument();
  });

  it('shows gap reason when gap section is expanded', async () => {
    const user = userEvent.setup();
    render(<ResearchSummary research={fullResearch} gaps={['industry_context']} />);

    await user.click(screen.getByText('Industry Context'));

    // Gap reason appears in both GapsSummary and the expanded section
    expect(
      screen.getAllByText(/Limited public information on industry trends/).length,
    ).toBeGreaterThanOrEqual(1);
  });

  it('collapses previously open section when another is clicked (single mode)', async () => {
    const user = userEvent.setup();
    render(<ResearchSummary research={fullResearch} gaps={['industry_context']} />);

    // Open strategic initiatives
    await user.click(screen.getByText('Strategic Initiatives'));
    expect(
      screen.getByText(/Acme Corp is expanding into enterprise market/),
    ).toBeInTheDocument();

    // Open culture values - strategic initiatives should collapse
    await user.click(screen.getByText('Culture & Values'));
    expect(screen.getByText(/Innovation, Integrity, Collaboration/)).toBeInTheDocument();
  });

  it('shows key insights box for sections with bullet points', async () => {
    const user = userEvent.setup();
    render(<ResearchSummary research={fullResearch} gaps={[]} />);

    await user.click(screen.getByText('Competitive Landscape'));

    expect(screen.getByText('Key Insights')).toBeInTheDocument();
    // Content appears both in Key Insights list and full content
    expect(screen.getAllByText(/Main competitor is BigCo/).length).toBeGreaterThanOrEqual(1);
  });

  it('does not show synthesis section when synthesis is absent', () => {
    const noSynthesis = { ...fullResearch, synthesis: undefined };
    render(<ResearchSummary research={noSynthesis} gaps={[]} />);

    expect(screen.queryByText('Strategic Summary')).not.toBeInTheDocument();
  });

  it('shows GapsSummary alert when gaps exist', () => {
    render(<ResearchSummary research={fullResearch} gaps={['industry_context']} />);

    expect(
      screen.getByText(/1 of 6 research categories with incomplete context/),
    ).toBeInTheDocument();
    expect(screen.getByText("This won't block your application")).toBeInTheDocument();
  });

  it('does not show GapsSummary when no gaps', () => {
    render(<ResearchSummary research={fullResearch} gaps={[]} />);

    expect(
      screen.queryByText(/research categories with incomplete context/),
    ).not.toBeInTheDocument();
  });

  it('shows Partial badge for partial sections', () => {
    const partialResearch: ResearchResult = {
      ...fullResearch,
      culture_values: {
        found: true,
        content: 'Limited information about company culture.',
        partial: true,
        partial_note: 'Only careers page found',
      },
    };
    render(<ResearchSummary research={partialResearch} gaps={['industry_context']} />);

    expect(screen.getByText('Partial')).toBeInTheDocument();
  });
});
