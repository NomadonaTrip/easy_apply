import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ResearchProgress } from './ResearchProgress';
import type { ResearchSourceState } from '@/hooks/useResearchStream';

function createSources(overrides: Partial<Record<string, Partial<ResearchSourceState>>> = {}): ResearchSourceState[] {
  const defaults: ResearchSourceState[] = [
    { source: 'strategic_initiatives', status: 'pending' },
    { source: 'competitive_landscape', status: 'pending' },
    { source: 'news_momentum', status: 'pending' },
    { source: 'industry_context', status: 'pending' },
    { source: 'culture_values', status: 'pending' },
    { source: 'leadership_direction', status: 'pending' },
  ];
  return defaults.map((s) => ({ ...s, ...overrides[s.source] }));
}

describe('ResearchProgress', () => {
  it('renders all 6 categories', () => {
    render(<ResearchProgress sources={createSources()} progress={0} isComplete={false} />);

    expect(screen.getByText('Strategic Initiatives')).toBeInTheDocument();
    expect(screen.getByText('Competitive Landscape')).toBeInTheDocument();
    expect(screen.getByText('Recent News & Momentum')).toBeInTheDocument();
    expect(screen.getByText('Industry Context')).toBeInTheDocument();
    expect(screen.getByText('Culture & Values')).toBeInTheDocument();
    expect(screen.getByText('Leadership Direction')).toBeInTheDocument();
  });

  it('shows 0/6 when no categories complete', () => {
    render(<ResearchProgress sources={createSources()} progress={0} isComplete={false} />);
    expect(screen.getByText('0/6 categories')).toBeInTheDocument();
  });

  it('shows correct count when some categories complete', () => {
    const sources = createSources({
      strategic_initiatives: { status: 'complete', found: true },
      competitive_landscape: { status: 'running', message: 'Analyzing...' },
    });
    render(<ResearchProgress sources={sources} progress={17} isComplete={false} />);
    expect(screen.getByText('1/6 categories')).toBeInTheDocument();
  });

  it('shows "Waiting..." for pending sources', () => {
    render(<ResearchProgress sources={createSources()} progress={0} isComplete={false} />);
    const waitingElements = screen.getAllByText('Waiting...');
    expect(waitingElements).toHaveLength(6);
  });

  it('shows custom message for running sources', () => {
    const sources = createSources({
      strategic_initiatives: { status: 'running', message: 'Investigating strategic initiatives...' },
    });
    render(<ResearchProgress sources={sources} progress={0} isComplete={false} />);
    expect(screen.getByText('Investigating strategic initiatives...')).toBeInTheDocument();
  });

  it('shows "Complete" for successful sources', () => {
    const sources = createSources({
      strategic_initiatives: { status: 'complete', found: true },
    });
    render(<ResearchProgress sources={sources} progress={17} isComplete={false} />);
    expect(screen.getByText('Complete')).toBeInTheDocument();
  });

  it('shows "Not found" for failed sources', () => {
    const sources = createSources({
      news_momentum: { status: 'failed', found: false },
    });
    render(<ResearchProgress sources={sources} progress={17} isComplete={false} />);
    expect(screen.getByText('Not found')).toBeInTheDocument();
  });

  it('shows gap warning message when complete with failures', () => {
    const sources = createSources({
      strategic_initiatives: { status: 'complete', found: true },
      competitive_landscape: { status: 'complete', found: true },
      news_momentum: { status: 'failed', found: false },
      industry_context: { status: 'complete', found: true },
      culture_values: { status: 'complete', found: true },
      leadership_direction: { status: 'complete', found: true },
    });
    render(<ResearchProgress sources={sources} progress={100} isComplete={true} />);
    expect(screen.getByText(/some sources had limited information/i)).toBeInTheDocument();
  });

  it('does not show gap warning when complete without failures', () => {
    const sources = createSources({
      strategic_initiatives: { status: 'complete', found: true },
      competitive_landscape: { status: 'complete', found: true },
      news_momentum: { status: 'complete', found: true },
      industry_context: { status: 'complete', found: true },
      culture_values: { status: 'complete', found: true },
      leadership_direction: { status: 'complete', found: true },
    });
    render(<ResearchProgress sources={sources} progress={100} isComplete={true} />);
    expect(screen.queryByText(/some sources had limited information/i)).not.toBeInTheDocument();
  });

  it('has accessible progress bar with aria values', () => {
    render(<ResearchProgress sources={createSources()} progress={50} isComplete={false} />);
    const progressBar = screen.getByRole('progressbar');
    expect(progressBar).toBeInTheDocument();
    expect(progressBar).toHaveAttribute('aria-valuenow', '50');
  });
});
