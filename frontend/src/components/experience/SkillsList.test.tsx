import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SkillsList } from './SkillsList';

// Mock the hooks
vi.mock('@/hooks/useExperience', () => ({
  useSkills: vi.fn(),
}));

import { useSkills } from '@/hooks/useExperience';

describe('SkillsList', () => {
  let queryClient: QueryClient;

  const mockSkills = [
    {
      id: 1,
      role_id: 1,
      name: 'Python',
      category: 'Programming',
      source: 'resume',
      created_at: '2026-01-01T00:00:00Z',
    },
    {
      id: 2,
      role_id: 1,
      name: 'FastAPI',
      category: 'Programming',
      source: 'resume',
      created_at: '2026-01-01T00:00:00Z',
    },
    {
      id: 3,
      role_id: 1,
      name: 'React',
      category: 'Frontend',
      source: 'resume',
      created_at: '2026-01-01T00:00:00Z',
    },
    {
      id: 4,
      role_id: 1,
      name: 'Leadership',
      category: null,
      source: 'resume',
      created_at: '2026-01-01T00:00:00Z',
    },
  ];

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
  });

  it('should show loading state', () => {
    vi.mocked(useSkills).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as ReturnType<typeof useSkills>);

    render(<SkillsList />, { wrapper });

    // Loading state shows a div with animate-pulse class
    const loadingElement = document.querySelector('.animate-pulse');
    expect(loadingElement).toBeInTheDocument();
  });

  it('should show error state when fetching fails', () => {
    vi.mocked(useSkills).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Failed to fetch'),
    } as ReturnType<typeof useSkills>);

    render(<SkillsList />, { wrapper });

    expect(screen.getByText(/failed to load skills/i)).toBeInTheDocument();
  });

  it('should show empty state when no skills exist', () => {
    vi.mocked(useSkills).mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    } as ReturnType<typeof useSkills>);

    render(<SkillsList />, { wrapper });

    expect(screen.getByText(/no skills extracted yet/i)).toBeInTheDocument();
    expect(screen.getByText(/upload a resume to get started/i)).toBeInTheDocument();
  });

  it('should display skills grouped by category', () => {
    vi.mocked(useSkills).mockReturnValue({
      data: mockSkills,
      isLoading: false,
      error: null,
    } as ReturnType<typeof useSkills>);

    render(<SkillsList />, { wrapper });

    // Check category headers
    expect(screen.getByText(/programming \(2\)/i)).toBeInTheDocument();
    expect(screen.getByText(/frontend \(1\)/i)).toBeInTheDocument();
    expect(screen.getByText(/uncategorized \(1\)/i)).toBeInTheDocument();

    // Check skill names
    expect(screen.getByText('Python')).toBeInTheDocument();
    expect(screen.getByText('FastAPI')).toBeInTheDocument();
    expect(screen.getByText('React')).toBeInTheDocument();
    expect(screen.getByText('Leadership')).toBeInTheDocument();
  });

  it('should show total count badge', () => {
    vi.mocked(useSkills).mockReturnValue({
      data: mockSkills,
      isLoading: false,
      error: null,
    } as ReturnType<typeof useSkills>);

    render(<SkillsList />, { wrapper });

    expect(screen.getByText('4 total')).toBeInTheDocument();
  });

  it('should sort categories alphabetically with Uncategorized last', () => {
    vi.mocked(useSkills).mockReturnValue({
      data: mockSkills,
      isLoading: false,
      error: null,
    } as ReturnType<typeof useSkills>);

    render(<SkillsList />, { wrapper });

    const categories = screen.getAllByRole('heading', { level: 4 });
    const categoryTexts = categories.map((h) => h.textContent);

    // Frontend should come before Programming, Uncategorized should be last
    expect(categoryTexts[0]).toMatch(/frontend/i);
    expect(categoryTexts[1]).toMatch(/programming/i);
    expect(categoryTexts[2]).toMatch(/uncategorized/i);
  });
});
