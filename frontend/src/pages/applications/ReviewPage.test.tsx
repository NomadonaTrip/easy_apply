import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClientProvider, QueryClient } from '@tanstack/react-query';
import { ReviewPage } from './ReviewPage';
import * as applicationsApi from '@/api/applications';
import type { Application } from '@/api/applications';
import { useRoleStore } from '@/stores/roleStore';

vi.mock('@/api/applications', () => ({
  getApplication: vi.fn(),
  getApplications: vi.fn(),
  createApplication: vi.fn(),
  extractKeywords: vi.fn(),
  saveKeywords: vi.fn(),
  updateApplicationStatus: vi.fn(),
  startResearch: vi.fn(),
  approveResearch: vi.fn(),
}));

const mockResearchData = JSON.stringify({
  strategic_initiatives: {
    found: true,
    content: 'Expanding into enterprise SaaS market',
  },
  competitive_landscape: {
    found: true,
    content: '- Main competitor is BigCo\n- Differentiates on price',
  },
  industry_context: {
    found: false,
    reason: 'Limited public data available',
  },
  synthesis: 'Company needs senior engineers to scale platform.',
  gaps: ['industry_context'],
  completed_at: '2026-02-09T12:00:00Z',
});

const mockApplication: Application = {
  id: 1,
  role_id: 1,
  company_name: 'Acme Corp',
  job_posting: 'Senior Engineer',
  job_url: 'https://acme.com/jobs/1',
  status: 'researching',
  keywords: null,
  research_data: mockResearchData,
  manual_context: null,
  generation_status: 'idle',
  resume_content: null,
  cover_letter_content: null,
  cover_letter_tone: null,
  resume_violations_fixed: null,
  resume_constraint_warnings: null,
  cover_letter_violations_fixed: null,
  cover_letter_constraint_warnings: null,
  created_at: '2026-02-01T00:00:00Z',
  updated_at: '2026-02-09T00:00:00Z',
};

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
}

function renderPage(initialEntry = '/applications/1/review') {
  // Set a current role in the store so apiRequest doesn't throw
  useRoleStore.setState({
    currentRole: { id: 1, user_id: 1, name: 'Dev', created_at: '2026-01-01' },
  });

  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route path="/applications/:id/review" element={<ReviewPage />} />
          <Route path="/applications/:id/research" element={<div>Research Page</div>} />
          <Route path="/applications/:id/export" element={<div>Export Page</div>} />
          <Route path="/applications/:id/context" element={<div>Context Page</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('ReviewPage', () => {
  it('shows loading skeleton while fetching', () => {
    vi.mocked(applicationsApi.getApplication).mockImplementation(
      () => new Promise(() => {}), // never resolves
    );
    renderPage();

    // Skeleton elements should be visible
    expect(document.querySelector('.animate-pulse')).toBeInTheDocument();
  });

  it('shows error state when fetch fails', async () => {
    vi.mocked(applicationsApi.getApplication).mockRejectedValue(new Error('Network error'));
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Failed to load application data')).toBeInTheDocument();
    });
  });

  it('displays research summary when data is loaded', async () => {
    vi.mocked(applicationsApi.getApplication).mockResolvedValue(mockApplication);
    renderPage();

    await waitFor(() => {
      expect(screen.getByText(/Research Summary: Acme Corp/)).toBeInTheDocument();
    });

    expect(screen.getByText('Strategic Initiatives')).toBeInTheDocument();
    expect(screen.getByText('Industry Context')).toBeInTheDocument();
  });

  it('shows synthesis text', async () => {
    vi.mocked(applicationsApi.getApplication).mockResolvedValue(mockApplication);
    renderPage();

    await waitFor(() => {
      expect(
        screen.getByText('Company needs senior engineers to scale platform.'),
      ).toBeInTheDocument();
    });
  });

  it('shows empty state when no research data', async () => {
    vi.mocked(applicationsApi.getApplication).mockResolvedValue({
      ...mockApplication,
      research_data: null,
    });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('No research data available.')).toBeInTheDocument();
    });
  });

  it('shows gap indicator for missing sections', async () => {
    vi.mocked(applicationsApi.getApplication).mockResolvedValue(mockApplication);
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Limited Info')).toBeInTheDocument();
    });
  });

  it('renders continue button', async () => {
    vi.mocked(applicationsApi.getApplication).mockResolvedValue(mockApplication);
    renderPage();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /continue to generation/i })).toBeInTheDocument();
    });
  });

  it('navigates to export on continue click after approval', async () => {
    const user = userEvent.setup();
    vi.mocked(applicationsApi.getApplication).mockResolvedValue(mockApplication);
    vi.mocked(applicationsApi.approveResearch).mockResolvedValue({
      application_id: 1,
      status: 'reviewed',
      approved_at: '2026-02-09T12:00:00Z',
      research_summary: { sources_found: 5, gaps: ['industry_context'], has_manual_context: false },
      message: 'Research approved. Ready for document generation.',
    });
    renderPage();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /continue to generation/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /continue to generation/i }));

    await waitFor(() => {
      expect(screen.getByText('Export Page')).toBeInTheDocument();
    });
  });

  it('renders back button that navigates to research', async () => {
    const user = userEvent.setup();
    vi.mocked(applicationsApi.getApplication).mockResolvedValue(mockApplication);
    renderPage();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /back/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /back/i }));

    expect(screen.getByText('Research Page')).toBeInTheDocument();
  });

  it('renders wizard step indicator at step 4', async () => {
    vi.mocked(applicationsApi.getApplication).mockResolvedValue(mockApplication);
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Review')).toBeInTheDocument();
    });
  });

  it('expands accordion section on click', async () => {
    const user = userEvent.setup();
    vi.mocked(applicationsApi.getApplication).mockResolvedValue(mockApplication);
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Strategic Initiatives')).toBeInTheDocument();
    });

    await user.click(screen.getByText('Strategic Initiatives'));

    expect(screen.getByText(/Expanding into enterprise SaaS market/)).toBeInTheDocument();
  });

  it('shows gap reason when gap section is expanded', async () => {
    const user = userEvent.setup();
    vi.mocked(applicationsApi.getApplication).mockResolvedValue(mockApplication);
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Industry Context')).toBeInTheDocument();
    });

    await user.click(screen.getByText('Industry Context'));

    // Text appears in both GapsSummary and the expanded section
    expect(screen.getAllByText(/Limited public data available/).length).toBeGreaterThanOrEqual(1);
  });

  it('shows approval confirmation section with sources count', async () => {
    vi.mocked(applicationsApi.getApplication).mockResolvedValue(mockApplication);
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Ready to Generate Documents')).toBeInTheDocument();
    });

    expect(screen.getByText('5 sources')).toBeInTheDocument();
    expect(screen.getByText('1 gap')).toBeInTheDocument();
  });

  it('shows pre-approval checklist items', async () => {
    vi.mocked(applicationsApi.getApplication).mockResolvedValue(mockApplication);
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("You've reviewed the research summary")).toBeInTheDocument();
    });

    expect(screen.getByText('The company information looks accurate')).toBeInTheDocument();
    expect(screen.getByText('You accept proceeding with research gaps')).toBeInTheDocument();
  });

  it('shows gap acknowledgment message in approval section', async () => {
    vi.mocked(applicationsApi.getApplication).mockResolvedValue(mockApplication);
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Proceeding with limited research')).toBeInTheDocument();
    });
  });

  it('shows add context button that navigates to context page', async () => {
    const user = userEvent.setup();
    vi.mocked(applicationsApi.getApplication).mockResolvedValue(mockApplication);
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Ready to Generate Documents')).toBeInTheDocument();
    });

    // Click the "Add Context" button within the approval confirmation
    const addContextButtons = screen.getAllByRole('button', { name: /add context/i });
    await user.click(addContextButtons[addContextButtons.length - 1]);

    expect(screen.getByText('Context Page')).toBeInTheDocument();
  });

  it('shows manual context display when context exists', async () => {
    vi.mocked(applicationsApi.getApplication).mockResolvedValue({
      ...mockApplication,
      manual_context: 'The company recently won an innovation award.',
    });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Your Additional Context')).toBeInTheDocument();
    });

    expect(screen.getByText('The company recently won an innovation award.')).toBeInTheDocument();
  });

  it('shows already-approved button when status is reviewed', async () => {
    vi.mocked(applicationsApi.getApplication).mockResolvedValue({
      ...mockApplication,
      status: 'reviewed',
    });
    renderPage();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /already approved/i })).toBeInTheDocument();
    });
  });

  it('calls approveResearch on continue click', async () => {
    const user = userEvent.setup();
    vi.mocked(applicationsApi.getApplication).mockResolvedValue(mockApplication);
    vi.mocked(applicationsApi.approveResearch).mockResolvedValue({
      application_id: 1,
      status: 'reviewed',
      approved_at: '2026-02-09T12:00:00Z',
      research_summary: { sources_found: 5, gaps: ['industry_context'], has_manual_context: false },
      message: 'Research approved. Ready for document generation.',
    });
    renderPage();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /continue to generation/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /continue to generation/i }));

    expect(applicationsApi.approveResearch).toHaveBeenCalledWith(1);
  });
});
