import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ExperiencePage } from './ExperiencePage';

// Mock the stores
vi.mock('@/stores/roleStore', () => ({
  useRoleStore: vi.fn(),
}));

// Mock the hooks
vi.mock('@/hooks/useExperience', () => ({
  useExperienceStats: vi.fn(),
  useSkills: vi.fn(),
  useAccomplishments: vi.fn(),
}));

// Mock the components to simplify testing
vi.mock('@/components/resumes', () => ({
  ResumeUploader: () => <div data-testid="resume-uploader">ResumeUploader</div>,
}));

vi.mock('@/components/experience', () => ({
  SkillsList: () => <div data-testid="skills-list">SkillsList</div>,
  AccomplishmentsList: () => <div data-testid="accomplishments-list">AccomplishmentsList</div>,
}));

import { useRoleStore } from '@/stores/roleStore';
import { useExperienceStats } from '@/hooks/useExperience';

describe('ExperiencePage', () => {
  let queryClient: QueryClient;

  const mockRole = {
    id: 1,
    user_id: 1,
    name: 'Software Engineer',
    created_at: '2026-01-01T00:00:00Z',
  };

  const mockStats = {
    total_skills: 15,
    total_accomplishments: 8,
    skills_by_category: {
      Programming: 5,
      Frontend: 4,
      Backend: 3,
      Uncategorized: 3,
    },
  };

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

  it('should show message when no role is selected', () => {
    vi.mocked(useRoleStore).mockReturnValue(null);
    vi.mocked(useExperienceStats).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    } as ReturnType<typeof useExperienceStats>);

    render(<ExperiencePage />, { wrapper });

    expect(screen.getByText(/please select a role/i)).toBeInTheDocument();
  });

  it('should display page title and role name', () => {
    vi.mocked(useRoleStore).mockReturnValue(mockRole);
    vi.mocked(useExperienceStats).mockReturnValue({
      data: mockStats,
      isLoading: false,
      error: null,
    } as ReturnType<typeof useExperienceStats>);

    render(<ExperiencePage />, { wrapper });

    expect(screen.getByText('Experience Database')).toBeInTheDocument();
    expect(screen.getByText(/role: software engineer/i)).toBeInTheDocument();
  });

  it('should display stats cards with counts', () => {
    vi.mocked(useRoleStore).mockReturnValue(mockRole);
    vi.mocked(useExperienceStats).mockReturnValue({
      data: mockStats,
      isLoading: false,
      error: null,
    } as ReturnType<typeof useExperienceStats>);

    render(<ExperiencePage />, { wrapper });

    expect(screen.getByText('15')).toBeInTheDocument();
    expect(screen.getByText('8')).toBeInTheDocument();
  });

  it('should render tabs for Skills, Accomplishments, and Upload', () => {
    vi.mocked(useRoleStore).mockReturnValue(mockRole);
    vi.mocked(useExperienceStats).mockReturnValue({
      data: mockStats,
      isLoading: false,
      error: null,
    } as ReturnType<typeof useExperienceStats>);

    render(<ExperiencePage />, { wrapper });

    expect(screen.getByRole('tab', { name: /skills/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /accomplishments/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /upload resumes/i })).toBeInTheDocument();
  });

  it('should show SkillsList component by default (skills tab)', () => {
    vi.mocked(useRoleStore).mockReturnValue(mockRole);
    vi.mocked(useExperienceStats).mockReturnValue({
      data: mockStats,
      isLoading: false,
      error: null,
    } as ReturnType<typeof useExperienceStats>);

    render(<ExperiencePage />, { wrapper });

    expect(screen.getByTestId('skills-list')).toBeInTheDocument();
  });

  it('should not display stats cards when stats not loaded', () => {
    vi.mocked(useRoleStore).mockReturnValue(mockRole);
    vi.mocked(useExperienceStats).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as ReturnType<typeof useExperienceStats>);

    render(<ExperiencePage />, { wrapper });

    // Stats values should not be present
    expect(screen.queryByText('15')).not.toBeInTheDocument();
    expect(screen.queryByText('8')).not.toBeInTheDocument();
  });
});
