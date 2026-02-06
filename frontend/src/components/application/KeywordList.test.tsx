import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { KeywordList } from './KeywordList';
import type { Keyword } from '@/api/applications';

const mockKeywords: Keyword[] = [
  { text: 'Python', priority: 9, category: 'technical_skill' },
  { text: 'Leadership', priority: 7, category: 'soft_skill' },
  { text: 'Agile', priority: 8, category: 'tool' },
  { text: 'Communication', priority: 5, category: 'soft_skill' },
];

describe('KeywordList', () => {
  it('renders all keywords', () => {
    render(<KeywordList keywords={mockKeywords} />);

    expect(screen.getByText('Python')).toBeInTheDocument();
    expect(screen.getByText('Leadership')).toBeInTheDocument();
    expect(screen.getByText('Agile')).toBeInTheDocument();
    expect(screen.getByText('Communication')).toBeInTheDocument();
  });

  it('displays priority numbers for each keyword', () => {
    render(<KeywordList keywords={mockKeywords} />);

    expect(screen.getByText('9')).toBeInTheDocument();
    expect(screen.getByText('7')).toBeInTheDocument();
    expect(screen.getByText('8')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
  });

  it('displays category badges', () => {
    render(<KeywordList keywords={mockKeywords} />);

    expect(screen.getByText('technical skill')).toBeInTheDocument();
    expect(screen.getAllByText('soft skill')).toHaveLength(2);
    expect(screen.getByText('tool')).toBeInTheDocument();
  });

  it('uses list semantics for accessibility', () => {
    render(<KeywordList keywords={mockKeywords} />);

    expect(screen.getByRole('list')).toBeInTheDocument();
    expect(screen.getAllByRole('listitem')).toHaveLength(4);
  });

  it('shows priority as aria-label for screen readers', () => {
    render(<KeywordList keywords={mockKeywords} />);

    expect(screen.getByLabelText('Priority 9 out of 10')).toBeInTheDocument();
    expect(screen.getByLabelText('Priority 7 out of 10')).toBeInTheDocument();
  });

  it('shows rank numbers', () => {
    render(<KeywordList keywords={mockKeywords} />);

    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('4')).toBeInTheDocument();
  });

  it('renders empty list without errors', () => {
    render(<KeywordList keywords={[]} />);

    expect(screen.getByRole('list')).toBeInTheDocument();
    expect(screen.queryAllByRole('listitem')).toHaveLength(0);
  });
});
