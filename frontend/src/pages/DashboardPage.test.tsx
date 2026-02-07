import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClientProvider, QueryClient } from '@tanstack/react-query';
import { DashboardPage } from './DashboardPage';
import { TooltipProvider } from '@/components/ui/tooltip';
import { useRoleStore } from '@/stores/roleStore';
import * as applicationsApi from '@/api/applications';

// Mock stores and API
vi.mock('@/stores/roleStore');
vi.mock('@/api/applications');

// Mock RoleSelector to avoid nested store calls from Sidebar
vi.mock('@/components/roles/RoleSelector', () => ({
  RoleSelector: () => <div data-testid="role-selector">RoleSelector</div>,
}));

const mockUseRoleStore = useRoleStore as unknown as ReturnType<typeof vi.fn>;

const storeState = (currentRole: { id: number; name: string } | null) => {
  const state = { currentRole, setCurrentRole: vi.fn() };
  return (selector?: (s: typeof state) => unknown) =>
    selector ? selector(state) : state;
};

const mockApplications: applicationsApi.Application[] = [
  {
    id: 1,
    role_id: 1,
    company_name: 'Acme Corp',
    job_posting: 'Developer role',
    job_url: null,
    status: 'created',
    keywords: null,
    research_data: null,
    resume_content: null,
    cover_letter_content: null,
    created_at: '2026-02-01T10:00:00Z',
    updated_at: '2026-02-01T10:00:00Z',
  },
  {
    id: 2,
    role_id: 1,
    company_name: 'TechStart',
    job_posting: 'Engineer',
    job_url: null,
    status: 'keywords',
    keywords: null,
    research_data: null,
    resume_content: null,
    cover_letter_content: null,
    created_at: '2026-02-02T10:00:00Z',
    updated_at: '2026-02-03T10:00:00Z',
  },
];

function renderDashboard() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <TooltipProvider>
          <DashboardPage />
        </TooltipProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows role selection prompt when no role selected', () => {
    mockUseRoleStore.mockImplementation(storeState(null));
    renderDashboard();
    expect(screen.getByText(/Select a role/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Manage Roles/i })).toBeInTheDocument();
  });

  it('shows loading state', () => {
    mockUseRoleStore.mockImplementation(storeState({ id: 1, name: 'Dev' }));
    vi.mocked(applicationsApi.getApplications).mockReturnValue(new Promise(() => {}));
    renderDashboard();
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('shows empty state when no applications exist', async () => {
    mockUseRoleStore.mockImplementation(storeState({ id: 1, name: 'Dev' }));
    vi.mocked(applicationsApi.getApplications).mockResolvedValue([]);
    renderDashboard();
    expect(await screen.findByText(/No applications yet/i)).toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: /New Application/i }).length).toBeGreaterThanOrEqual(1);
  });

  it('lists applications when they exist', async () => {
    mockUseRoleStore.mockImplementation(storeState({ id: 1, name: 'Dev' }));
    vi.mocked(applicationsApi.getApplications).mockResolvedValue(mockApplications);
    const { container } = renderDashboard();
    // Wait for loading to finish (heading appears after data loads)
    await screen.findByRole('heading', { name: 'Applications' });
    // Applications should be visible in either table or card view
    expect(container.textContent).toContain('Acme Corp');
    expect(container.textContent).toContain('TechStart');
  });

  it('shows New Application button', async () => {
    mockUseRoleStore.mockImplementation(storeState({ id: 1, name: 'Dev' }));
    vi.mocked(applicationsApi.getApplications).mockResolvedValue([]);
    renderDashboard();
    await screen.findByText(/No applications yet/i);
    expect(screen.getAllByRole('link', { name: /New Application/i }).length).toBeGreaterThanOrEqual(1);
  });

  it('displays "Applications" heading', async () => {
    mockUseRoleStore.mockImplementation(storeState({ id: 1, name: 'Dev' }));
    vi.mocked(applicationsApi.getApplications).mockResolvedValue([]);
    renderDashboard();
    expect(await screen.findByRole('heading', { name: 'Applications' })).toBeInTheDocument();
  });
});
