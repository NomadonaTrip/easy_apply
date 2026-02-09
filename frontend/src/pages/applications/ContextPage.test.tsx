import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClientProvider, QueryClient } from '@tanstack/react-query';
import { ContextPage } from './ContextPage';
import * as applicationsApi from '@/api/applications';
import { useRoleStore } from '@/stores/roleStore';

vi.mock('@/api/applications', () => ({
  getApplication: vi.fn(),
  getApplications: vi.fn(),
  createApplication: vi.fn(),
  extractKeywords: vi.fn(),
  saveKeywords: vi.fn(),
  updateApplicationStatus: vi.fn(),
  startResearch: vi.fn(),
  getManualContext: vi.fn(),
  saveManualContext: vi.fn(),
}));

const mockContextResponse: applicationsApi.ManualContextResponse = {
  application_id: 1,
  manual_context: '',
  gaps: ['strategic_initiatives', 'culture_values'],
};

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
}

function renderPage(initialEntry = '/applications/1/context') {
  useRoleStore.setState({
    currentRole: { id: 1, user_id: 1, name: 'Dev', created_at: '2026-01-01' },
  });

  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route path="/applications/:id/context" element={<ContextPage />} />
          <Route path="/applications/:id/review" element={<div>Review Page</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('ContextPage', () => {
  it('shows loading skeleton while fetching', () => {
    vi.mocked(applicationsApi.getManualContext).mockImplementation(
      () => new Promise(() => {}),
    );
    renderPage();

    expect(document.querySelector('.animate-pulse')).toBeInTheDocument();
  });

  it('shows error state when fetch fails', async () => {
    vi.mocked(applicationsApi.getManualContext).mockRejectedValue(
      new Error('Network error'),
    );
    renderPage();

    await waitFor(() => {
      expect(
        screen.getByText('Failed to load context data'),
      ).toBeInTheDocument();
    });
  });

  it('renders the form when data loads', async () => {
    vi.mocked(applicationsApi.getManualContext).mockResolvedValue(
      mockContextResponse,
    );
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Add Manual Context')).toBeInTheDocument();
    });

    expect(screen.getByLabelText('Additional Context')).toBeInTheDocument();
  });

  it('shows gap suggestions from API response', async () => {
    vi.mocked(applicationsApi.getManualContext).mockResolvedValue(
      mockContextResponse,
    );
    renderPage();

    await waitFor(() => {
      expect(
        screen.getByText('Suggestions Based on Missing Information'),
      ).toBeInTheDocument();
    });

    expect(screen.getByText(/strategic initiatives/i)).toBeInTheDocument();
    expect(screen.getByText(/culture values/i)).toBeInTheDocument();
  });

  it('loads existing context as initial value', async () => {
    vi.mocked(applicationsApi.getManualContext).mockResolvedValue({
      ...mockContextResponse,
      manual_context: 'Previously saved context',
    });
    renderPage();

    await waitFor(() => {
      expect(screen.getByLabelText('Additional Context')).toHaveValue(
        'Previously saved context',
      );
    });
  });

  it('saves context and navigates to review on success', async () => {
    const user = userEvent.setup();
    vi.mocked(applicationsApi.getManualContext).mockResolvedValue(
      mockContextResponse,
    );
    vi.mocked(applicationsApi.saveManualContext).mockResolvedValue({
      application_id: 1,
      manual_context: 'New context',
      message: 'Context saved successfully',
    });
    renderPage();

    await waitFor(() => {
      expect(screen.getByLabelText('Additional Context')).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText('Additional Context'), 'New context');
    await user.click(screen.getByRole('button', { name: /save context/i }));

    await waitFor(() => {
      expect(applicationsApi.saveManualContext).toHaveBeenCalledWith(
        1,
        'New context',
      );
    });

    await waitFor(() => {
      expect(screen.getByText('Review Page')).toBeInTheDocument();
    });
  });

  it('navigates to review on cancel', async () => {
    const user = userEvent.setup();
    vi.mocked(applicationsApi.getManualContext).mockResolvedValue(
      mockContextResponse,
    );
    renderPage();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /cancel/i }));

    expect(screen.getByText('Review Page')).toBeInTheDocument();
  });

  it('navigates to review via back button', async () => {
    const user = userEvent.setup();
    vi.mocked(applicationsApi.getManualContext).mockResolvedValue(
      mockContextResponse,
    );
    renderPage();

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: /back to review/i }),
      ).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /back to review/i }));

    expect(screen.getByText('Review Page')).toBeInTheDocument();
  });
});
