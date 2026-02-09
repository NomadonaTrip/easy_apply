import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ResearchSection } from './ResearchSection';

describe('ResearchSection', () => {
  it('renders gap styling when isGap is true', () => {
    render(<ResearchSection content={null} reason="Could not find data" isGap={true} />);

    expect(screen.getByText('Limited Information Available')).toBeInTheDocument();
    expect(screen.getByText('Could not find data')).toBeInTheDocument();
  });

  it('renders default gap message when no reason provided', () => {
    render(<ResearchSection content={null} reason={null} isGap={true} />);

    expect(
      screen.getByText(
        "This information couldn't be found during research. You can add context manually if needed.",
      ),
    ).toBeInTheDocument();
  });

  it('renders gap styling when content is null even if isGap is false', () => {
    render(<ResearchSection content={null} reason={null} isGap={false} />);

    expect(screen.getByText('Limited Information Available')).toBeInTheDocument();
  });

  it('renders content when found', () => {
    render(
      <ResearchSection
        content="Acme Corp is expanding into enterprise SaaS"
        reason={null}
        isGap={false}
      />,
    );

    expect(
      screen.getByText('Acme Corp is expanding into enterprise SaaS'),
    ).toBeInTheDocument();
    expect(screen.queryByText('Limited Information Available')).not.toBeInTheDocument();
  });

  it('shows key insights box when content has bullet points', () => {
    const content = '- Key finding one\n- Key finding two\nSome other text';
    render(<ResearchSection content={content} reason={null} isGap={false} />);

    expect(screen.getByText('Key Insights')).toBeInTheDocument();
    expect(screen.getByText('Key finding one')).toBeInTheDocument();
    expect(screen.getByText('Key finding two')).toBeInTheDocument();
  });

  it('does not show key insights when content has no bullet points', () => {
    const content = 'Just regular paragraph text without any bullets.';
    render(<ResearchSection content={content} reason={null} isGap={false} />);

    expect(screen.queryByText('Key Insights')).not.toBeInTheDocument();
  });

  it('limits key insights to 5 items', () => {
    const content = Array.from({ length: 8 }, (_, i) => `- Insight ${i + 1}`).join('\n');
    render(<ResearchSection content={content} reason={null} isGap={false} />);

    expect(screen.getByText('Insight 1')).toBeInTheDocument();
    expect(screen.getByText('Insight 5')).toBeInTheDocument();
    // Key Insights <ul> should only contain 5 items (sliced from 8)
    const keyInsightsHeading = screen.getByText('Key Insights');
    const insightsContainer = keyInsightsHeading.closest('.p-4')!;
    const listItems = insightsContainer.querySelectorAll('li');
    expect(listItems.length).toBe(5);
  });

  it('shows partial warning when partial is true', () => {
    render(
      <ResearchSection
        content="Limited information about company culture from careers page."
        reason={null}
        isGap={false}
        partial={true}
        partialNote="Only careers page found, no additional public statements"
      />,
    );

    expect(screen.getByText('Partial Information')).toBeInTheDocument();
    expect(
      screen.getByText('Only careers page found, no additional public statements'),
    ).toBeInTheDocument();
    // Content should still be displayed
    expect(
      screen.getByText(/Limited information about company culture/),
    ).toBeInTheDocument();
  });

  it('shows default partial message when no partialNote provided', () => {
    render(
      <ResearchSection
        content="Some data here"
        reason={null}
        isGap={false}
        partial={true}
      />,
    );

    expect(screen.getByText('Partial Information')).toBeInTheDocument();
    expect(
      screen.getByText('Some information may be incomplete.'),
    ).toBeInTheDocument();
  });

  it('does not show partial warning when partial is false', () => {
    render(
      <ResearchSection
        content="Full detailed research content"
        reason={null}
        isGap={false}
        partial={false}
      />,
    );

    expect(screen.queryByText('Partial Information')).not.toBeInTheDocument();
  });
});
