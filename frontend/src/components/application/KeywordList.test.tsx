import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { KeywordList } from './KeywordList';
import type { KeywordWithId } from '@/api/applications';

const mockKeywords: KeywordWithId[] = [
  { _id: 'kw-0', text: 'Python', priority: 9, category: 'technical_skill' },
  { _id: 'kw-1', text: 'Leadership', priority: 7, category: 'soft_skill' },
  { _id: 'kw-2', text: 'Agile', priority: 8, category: 'tool' },
  { _id: 'kw-3', text: 'Communication', priority: 5, category: 'soft_skill' },
];

// Mock window.matchMedia for useMediaQuery hook
beforeEach(() => {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false, // Default: desktop mode
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
});

describe('KeywordList', () => {
  it('renders all keywords', () => {
    render(<KeywordList keywords={mockKeywords} onReorder={vi.fn()} />);

    expect(screen.getByText('Python')).toBeInTheDocument();
    expect(screen.getByText('Leadership')).toBeInTheDocument();
    expect(screen.getByText('Agile')).toBeInTheDocument();
    expect(screen.getByText('Communication')).toBeInTheDocument();
  });

  it('displays priority numbers for each keyword', () => {
    render(<KeywordList keywords={mockKeywords} onReorder={vi.fn()} />);

    expect(screen.getByText('9')).toBeInTheDocument();
    expect(screen.getByText('7')).toBeInTheDocument();
    expect(screen.getByText('8')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
  });

  it('displays category badges', () => {
    render(<KeywordList keywords={mockKeywords} onReorder={vi.fn()} />);

    expect(screen.getByText('technical skill')).toBeInTheDocument();
    expect(screen.getAllByText('soft skill')).toHaveLength(2);
    expect(screen.getByText('tool')).toBeInTheDocument();
  });

  it('uses list semantics for accessibility', () => {
    render(<KeywordList keywords={mockKeywords} onReorder={vi.fn()} />);

    expect(screen.getByRole('list')).toBeInTheDocument();
    expect(screen.getAllByRole('listitem')).toHaveLength(4);
  });

  it('shows priority as aria-label for screen readers', () => {
    render(<KeywordList keywords={mockKeywords} onReorder={vi.fn()} />);

    expect(screen.getByLabelText('Priority 9 out of 10')).toBeInTheDocument();
    expect(screen.getByLabelText('Priority 7 out of 10')).toBeInTheDocument();
  });

  it('shows rank numbers', () => {
    render(<KeywordList keywords={mockKeywords} onReorder={vi.fn()} />);

    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('4')).toBeInTheDocument();
  });

  it('handles duplicate keyword texts with unique _id', () => {
    const duplicateKeywords: KeywordWithId[] = [
      { _id: 'kw-0', text: 'Python', priority: 9, category: 'technical_skill' },
      { _id: 'kw-1', text: 'Python', priority: 7, category: 'tool' },
    ];
    render(<KeywordList keywords={duplicateKeywords} onReorder={vi.fn()} />);

    expect(screen.getAllByText('Python')).toHaveLength(2);
    expect(screen.getAllByRole('listitem')).toHaveLength(2);
  });

  it('renders empty list without errors', () => {
    render(<KeywordList keywords={[]} onReorder={vi.fn()} />);

    expect(screen.getByRole('list')).toBeInTheDocument();
    expect(screen.queryAllByRole('listitem')).toHaveLength(0);
  });

  it('shows success pattern badge for boosted keywords', () => {
    const keywordsWithPattern: KeywordWithId[] = [
      { _id: 'kw-0', text: 'Python', priority: 9, category: 'technical_skill', pattern_boosted: true },
      { _id: 'kw-1', text: 'React', priority: 7, category: 'tool', pattern_boosted: false },
    ];
    render(<KeywordList keywords={keywordsWithPattern} onReorder={vi.fn()} />);

    expect(screen.getByText('Success pattern')).toBeInTheDocument();
    expect(screen.getAllByText('Success pattern')).toHaveLength(1);
  });

  it('does not show success pattern badge when no keywords are boosted', () => {
    render(<KeywordList keywords={mockKeywords} onReorder={vi.fn()} />);

    expect(screen.queryByText('Success pattern')).not.toBeInTheDocument();
  });

  it('shows drag handles on desktop', () => {
    render(<KeywordList keywords={mockKeywords} onReorder={vi.fn()} />);

    const dragHandles = screen.getAllByLabelText('Drag to reorder');
    expect(dragHandles).toHaveLength(4);
  });

  it('does not show up/down buttons on desktop', () => {
    render(<KeywordList keywords={mockKeywords} onReorder={vi.fn()} />);

    expect(screen.queryAllByLabelText('Move up')).toHaveLength(0);
    expect(screen.queryAllByLabelText('Move down')).toHaveLength(0);
  });
});

describe('KeywordList (mobile)', () => {
  beforeEach(() => {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: query === '(max-width: 768px)', // Mobile mode
        media: query,
        onchange: null,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    });
  });

  it('shows up/down buttons on mobile', () => {
    render(<KeywordList keywords={mockKeywords} onReorder={vi.fn()} />);

    expect(screen.getAllByLabelText('Move up')).toHaveLength(4);
    expect(screen.getAllByLabelText('Move down')).toHaveLength(4);
  });

  it('does not show drag handles on mobile', () => {
    render(<KeywordList keywords={mockKeywords} onReorder={vi.fn()} />);

    expect(screen.queryAllByLabelText('Drag to reorder')).toHaveLength(0);
  });

  it('disables up button on first item', () => {
    render(<KeywordList keywords={mockKeywords} onReorder={vi.fn()} />);

    const upButtons = screen.getAllByLabelText('Move up');
    expect(upButtons[0]).toBeDisabled();
  });

  it('disables down button on last item', () => {
    render(<KeywordList keywords={mockKeywords} onReorder={vi.fn()} />);

    const downButtons = screen.getAllByLabelText('Move down');
    expect(downButtons[downButtons.length - 1]).toBeDisabled();
  });

  it('calls onReorder when up button clicked', () => {
    const mockReorder = vi.fn();
    render(<KeywordList keywords={mockKeywords} onReorder={mockReorder} />);

    const upButtons = screen.getAllByLabelText('Move up');
    fireEvent.click(upButtons[1]); // Click "Move up" on second item (Leadership)

    expect(mockReorder).toHaveBeenCalledTimes(1);
    const reorderedKeywords = mockReorder.mock.calls[0][0];
    expect(reorderedKeywords[0].text).toBe('Leadership');
    expect(reorderedKeywords[1].text).toBe('Python');
  });

  it('calls onReorder when down button clicked', () => {
    const mockReorder = vi.fn();
    render(<KeywordList keywords={mockKeywords} onReorder={mockReorder} />);

    const downButtons = screen.getAllByLabelText('Move down');
    fireEvent.click(downButtons[0]); // Click "Move down" on first item (Python)

    expect(mockReorder).toHaveBeenCalledTimes(1);
    const reorderedKeywords = mockReorder.mock.calls[0][0];
    expect(reorderedKeywords[0].text).toBe('Leadership');
    expect(reorderedKeywords[1].text).toBe('Python');
  });

  it('does not call onReorder when clicking disabled up button on first item', () => {
    const mockReorder = vi.fn();
    render(<KeywordList keywords={mockKeywords} onReorder={mockReorder} />);

    const upButtons = screen.getAllByLabelText('Move up');
    fireEvent.click(upButtons[0]); // First item's up button - disabled

    expect(mockReorder).not.toHaveBeenCalled();
  });

  it('does not call onReorder when clicking disabled down button on last item', () => {
    const mockReorder = vi.fn();
    render(<KeywordList keywords={mockKeywords} onReorder={mockReorder} />);

    const downButtons = screen.getAllByLabelText('Move down');
    fireEvent.click(downButtons[downButtons.length - 1]); // Last item's down button - disabled

    expect(mockReorder).not.toHaveBeenCalled();
  });
});
