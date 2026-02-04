import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AccomplishmentsList } from './AccomplishmentsList';

// Mock the hooks
vi.mock('@/hooks/useExperience', () => ({
  useAccomplishments: vi.fn(),
}));

import { useAccomplishments } from '@/hooks/useExperience';

describe('AccomplishmentsList', () => {
  let queryClient: QueryClient;

  const mockAccomplishments = [
    {
      id: 1,
      role_id: 1,
      description: 'Led team of 5 developers',
      context: 'Tech Lead at StartupCo',
      source: 'resume',
      created_at: '2026-01-01T00:00:00Z',
    },
    {
      id: 2,
      role_id: 1,
      description: 'Reduced deployment time by 50%',
      context: null,
      source: 'application',
      created_at: '2026-01-02T00:00:00Z',
    },
    {
      id: 3,
      role_id: 1,
      description: 'Implemented CI/CD pipeline',
      context: 'DevOps initiative',
      source: null,
      created_at: '2026-01-03T00:00:00Z',
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
    vi.mocked(useAccomplishments).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as ReturnType<typeof useAccomplishments>);

    render(<AccomplishmentsList />, { wrapper });

    const loadingElement = document.querySelector('.animate-pulse');
    expect(loadingElement).toBeInTheDocument();
  });

  it('should show error state when fetching fails', () => {
    vi.mocked(useAccomplishments).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Failed to fetch'),
    } as ReturnType<typeof useAccomplishments>);

    render(<AccomplishmentsList />, { wrapper });

    expect(screen.getByText(/failed to load accomplishments/i)).toBeInTheDocument();
  });

  it('should show empty state when no accomplishments exist', () => {
    vi.mocked(useAccomplishments).mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    } as ReturnType<typeof useAccomplishments>);

    render(<AccomplishmentsList />, { wrapper });

    expect(screen.getByText(/no accomplishments extracted yet/i)).toBeInTheDocument();
    expect(screen.getByText(/upload a resume to get started/i)).toBeInTheDocument();
  });

  it('should display accomplishments with descriptions', () => {
    vi.mocked(useAccomplishments).mockReturnValue({
      data: mockAccomplishments,
      isLoading: false,
      error: null,
    } as ReturnType<typeof useAccomplishments>);

    render(<AccomplishmentsList />, { wrapper });

    expect(screen.getByText('Led team of 5 developers')).toBeInTheDocument();
    expect(screen.getByText('Reduced deployment time by 50%')).toBeInTheDocument();
    expect(screen.getByText('Implemented CI/CD pipeline')).toBeInTheDocument();
  });

  it('should display context when available', () => {
    vi.mocked(useAccomplishments).mockReturnValue({
      data: mockAccomplishments,
      isLoading: false,
      error: null,
    } as ReturnType<typeof useAccomplishments>);

    render(<AccomplishmentsList />, { wrapper });

    expect(screen.getByText('Tech Lead at StartupCo')).toBeInTheDocument();
    expect(screen.getByText('DevOps initiative')).toBeInTheDocument();
  });

  it('should display source labels when available', () => {
    vi.mocked(useAccomplishments).mockReturnValue({
      data: mockAccomplishments,
      isLoading: false,
      error: null,
    } as ReturnType<typeof useAccomplishments>);

    render(<AccomplishmentsList />, { wrapper });

    expect(screen.getByText('From resume')).toBeInTheDocument();
    expect(screen.getByText('From application')).toBeInTheDocument();
  });

  it('should show total count badge', () => {
    vi.mocked(useAccomplishments).mockReturnValue({
      data: mockAccomplishments,
      isLoading: false,
      error: null,
    } as ReturnType<typeof useAccomplishments>);

    render(<AccomplishmentsList />, { wrapper });

    expect(screen.getByText('3 total')).toBeInTheDocument();
  });
});
