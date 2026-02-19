/* eslint-disable @typescript-eslint/no-explicit-any */
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi } from 'vitest';
import { SkillsList } from '../SkillsList';
import { AccomplishmentsList } from '../AccomplishmentsList';

// Mock the hooks
vi.mock('@/hooks/useExperience', () => ({
  useSkills: vi.fn(),
  useAccomplishments: vi.fn(),
}));

import { useSkills, useAccomplishments } from '@/hooks/useExperience';

const mockUseSkills = vi.mocked(useSkills);
const mockUseAccomplishments = vi.mocked(useAccomplishments);

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe('SkillsList source badges', () => {
  it('renders "Resume" badge for resume-sourced skills', () => {
    mockUseSkills.mockReturnValue({
      data: [
        {
          id: 1,
          role_id: 1,
          name: 'Python',
          category: 'Language',
          source: 'resume',
          created_at: '2024-01-01T00:00:00Z',
        },
      ],
      isLoading: false,
      error: null,
    } as any);

    render(<SkillsList />, { wrapper: createWrapper() });

    expect(screen.getByText('Python')).toBeInTheDocument();
    expect(screen.getByText('Resume')).toBeInTheDocument();
  });

  it('renders "Enriched" badge for application-enriched skills', () => {
    mockUseSkills.mockReturnValue({
      data: [
        {
          id: 2,
          role_id: 1,
          name: 'Kubernetes',
          category: 'DevOps',
          source: 'application-enriched',
          created_at: '2024-01-01T00:00:00Z',
        },
      ],
      isLoading: false,
      error: null,
    } as any);

    render(<SkillsList />, { wrapper: createWrapper() });

    expect(screen.getByText('Kubernetes')).toBeInTheDocument();
    expect(screen.getByText('Enriched')).toBeInTheDocument();
  });

  it('does not render source badge when source is null', () => {
    mockUseSkills.mockReturnValue({
      data: [
        {
          id: 3,
          role_id: 1,
          name: 'Docker',
          category: 'DevOps',
          source: null,
          created_at: '2024-01-01T00:00:00Z',
        },
      ],
      isLoading: false,
      error: null,
    } as any);

    render(<SkillsList />, { wrapper: createWrapper() });

    expect(screen.getByText('Docker')).toBeInTheDocument();
    expect(screen.queryByText('Resume')).not.toBeInTheDocument();
    expect(screen.queryByText('Enriched')).not.toBeInTheDocument();
  });

  it('renders both source types when mixed', () => {
    mockUseSkills.mockReturnValue({
      data: [
        {
          id: 1,
          role_id: 1,
          name: 'Python',
          category: 'Language',
          source: 'resume',
          created_at: '2024-01-01T00:00:00Z',
        },
        {
          id: 2,
          role_id: 1,
          name: 'Terraform',
          category: 'Language',
          source: 'application-enriched',
          created_at: '2024-01-01T00:00:00Z',
        },
      ],
      isLoading: false,
      error: null,
    } as any);

    render(<SkillsList />, { wrapper: createWrapper() });

    expect(screen.getByText('Resume')).toBeInTheDocument();
    expect(screen.getByText('Enriched')).toBeInTheDocument();
  });
});

describe('AccomplishmentsList source badges', () => {
  it('renders "Enriched" badge for application-enriched accomplishments', () => {
    mockUseAccomplishments.mockReturnValue({
      data: [
        {
          id: 1,
          role_id: 1,
          description: 'Led migration to microservices',
          context: 'At TechCo',
          source: 'application-enriched',
          created_at: '2024-01-01T00:00:00Z',
        },
      ],
      isLoading: false,
      error: null,
    } as any);

    render(<AccomplishmentsList />, { wrapper: createWrapper() });

    expect(screen.getByText('Led migration to microservices')).toBeInTheDocument();
    expect(screen.getByText('Enriched')).toBeInTheDocument();
  });

  it('renders "From resume" badge for resume-sourced accomplishments', () => {
    mockUseAccomplishments.mockReturnValue({
      data: [
        {
          id: 2,
          role_id: 1,
          description: 'Reduced deployment time by 60%',
          context: null,
          source: 'resume',
          created_at: '2024-01-01T00:00:00Z',
        },
      ],
      isLoading: false,
      error: null,
    } as any);

    render(<AccomplishmentsList />, { wrapper: createWrapper() });

    expect(screen.getByText('Reduced deployment time by 60%')).toBeInTheDocument();
    expect(screen.getByText('From resume')).toBeInTheDocument();
  });

  it('does not render source badge when source is null', () => {
    mockUseAccomplishments.mockReturnValue({
      data: [
        {
          id: 3,
          role_id: 1,
          description: 'Improved system uptime to 99.9%',
          context: null,
          source: null,
          created_at: '2024-01-01T00:00:00Z',
        },
      ],
      isLoading: false,
      error: null,
    } as any);

    render(<AccomplishmentsList />, { wrapper: createWrapper() });

    expect(screen.getByText('Improved system uptime to 99.9%')).toBeInTheDocument();
    expect(screen.queryByText('From resume')).not.toBeInTheDocument();
    expect(screen.queryByText('Enriched')).not.toBeInTheDocument();
  });
});
