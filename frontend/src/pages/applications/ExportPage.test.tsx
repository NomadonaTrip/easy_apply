import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClientProvider, QueryClient } from '@tanstack/react-query';
import { ExportPage } from './ExportPage';
import * as applicationsApi from '@/api/applications';
import * as generationApi from '@/api/generation';
import { useRoleStore } from '@/stores/roleStore';
import type { Application } from '@/api/applications';

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

vi.mock('@/api/generation', () => ({
  generateResume: vi.fn(),
  generateCoverLetter: vi.fn(),
  getGenerationStatus: vi.fn(),
}));

const mockResearchData = JSON.stringify({
  strategic_initiatives: { found: true, content: 'test' },
  synthesis: 'test synthesis',
  gaps: [],
  completed_at: '2026-02-09T12:00:00Z',
});

const mockKeywords = JSON.stringify([
  { text: 'React', priority: 9, category: 'technical_skill' },
]);

const mockReviewedApp: Application = {
  id: 1,
  role_id: 1,
  company_name: 'Acme Corp',
  job_posting: 'Senior Engineer',
  job_url: 'https://acme.com/jobs/1',
  status: 'reviewed',
  keywords: mockKeywords,
  research_data: mockResearchData,
  manual_context: null,
  generation_status: 'idle',
  resume_content: null,
  cover_letter_content: null,
  created_at: '2026-02-01T00:00:00Z',
  updated_at: '2026-02-09T00:00:00Z',
};

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
}

function renderPage(initialEntry = '/applications/1/export') {
  useRoleStore.setState({
    currentRole: { id: 1, user_id: 1, name: 'Dev', created_at: '2026-01-01' },
  });

  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route path="/applications/:id/export" element={<ExportPage />} />
          <Route path="/applications/:id/review" element={<div>Review Page</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('ExportPage', () => {
  it('shows loading skeleton while fetching', () => {
    vi.mocked(applicationsApi.getApplication).mockImplementation(
      () => new Promise(() => {}),
    );
    renderPage();
    expect(document.querySelector('.animate-pulse')).toBeInTheDocument();
  });

  it('shows error state when fetch fails', async () => {
    vi.mocked(applicationsApi.getApplication).mockRejectedValue(new Error('Network error'));
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Failed to load application data')).toBeInTheDocument();
    });
  });

  it('renders wizard step indicator at step 5', async () => {
    vi.mocked(applicationsApi.getApplication).mockResolvedValue(mockReviewedApp);
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Export')).toBeInTheDocument();
    });
  });

  it('renders page header with company name', async () => {
    vi.mocked(applicationsApi.getApplication).mockResolvedValue(mockReviewedApp);
    renderPage();

    await waitFor(() => {
      expect(screen.getByText(/Generate Documents: Acme Corp/)).toBeInTheDocument();
    });
  });

  it('renders back button that navigates to review', async () => {
    const user = userEvent.setup();
    vi.mocked(applicationsApi.getApplication).mockResolvedValue(mockReviewedApp);
    renderPage();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /back/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /back/i }));
    expect(screen.getByText('Review Page')).toBeInTheDocument();
  });

  describe('prerequisite validation', () => {
    it('shows prerequisites warning when keywords are missing', async () => {
      vi.mocked(applicationsApi.getApplication).mockResolvedValue({
        ...mockReviewedApp,
        keywords: null,
      });
      renderPage();

      await waitFor(() => {
        expect(screen.getByText('Prerequisites not met')).toBeInTheDocument();
        expect(screen.getByText('Keywords must be extracted first')).toBeInTheDocument();
      });
    });

    it('shows prerequisites warning when research not approved', async () => {
      vi.mocked(applicationsApi.getApplication).mockResolvedValue({
        ...mockReviewedApp,
        status: 'keywords',
      });
      renderPage();

      await waitFor(() => {
        expect(screen.getByText('Prerequisites not met')).toBeInTheDocument();
        expect(screen.getByText('Research must be approved first')).toBeInTheDocument();
      });
    });

    it('does not show prerequisites warning when all prerequisites met', async () => {
      vi.mocked(applicationsApi.getApplication).mockResolvedValue(mockReviewedApp);
      renderPage();

      await waitFor(() => {
        expect(screen.getByText(/Generate Documents/)).toBeInTheDocument();
      });

      expect(screen.queryByText('Prerequisites not met')).not.toBeInTheDocument();
    });
  });

  describe('resume generation trigger', () => {
    it('shows Generate Resume button when no resume exists', async () => {
      vi.mocked(applicationsApi.getApplication).mockResolvedValue(mockReviewedApp);
      renderPage();

      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Generate Resume' })).toBeInTheDocument();
      });
    });

    it('shows empty state message when no resume exists', async () => {
      vi.mocked(applicationsApi.getApplication).mockResolvedValue(mockReviewedApp);
      renderPage();

      await waitFor(() => {
        expect(screen.getByText('No Resume Generated')).toBeInTheDocument();
      });
    });

    it('calls generateResume API on button click', async () => {
      const user = userEvent.setup();
      vi.mocked(applicationsApi.getApplication).mockResolvedValue(mockReviewedApp);
      vi.mocked(generationApi.generateResume).mockResolvedValue({
        message: 'Resume generated successfully',
        resume_content: '# Test Resume',
        status: 'complete',
      });
      renderPage();

      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Generate Resume' })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: 'Generate Resume' }));

      await waitFor(() => {
        expect(generationApi.generateResume).toHaveBeenCalledWith(1);
      });
    });

    it('shows loading state during generation', async () => {
      const user = userEvent.setup();
      vi.mocked(applicationsApi.getApplication).mockResolvedValue(mockReviewedApp);
      vi.mocked(generationApi.generateResume).mockImplementation(
        () => new Promise(() => {}),
      );
      renderPage();

      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Generate Resume' })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: 'Generate Resume' }));

      await waitFor(() => {
        expect(screen.getByText('Generating Resume...')).toBeInTheDocument();
      });
    });
  });

  describe('resume preview', () => {
    it('displays generated resume content', async () => {
      vi.mocked(applicationsApi.getApplication).mockResolvedValue({
        ...mockReviewedApp,
        resume_content: '# John Doe\n\nSenior Engineer with 5 years experience',
        generation_status: 'complete',
      });
      renderPage();

      await waitFor(() => {
        expect(screen.getByText('Resume Preview')).toBeInTheDocument();
      });

      expect(screen.getByText('John Doe')).toBeInTheDocument();
      expect(screen.getByText(/Senior Engineer with 5 years experience/)).toBeInTheDocument();
    });

    it('shows Generated badge with timestamp when resume exists', async () => {
      vi.mocked(applicationsApi.getApplication).mockResolvedValue({
        ...mockReviewedApp,
        resume_content: '# Resume',
        generation_status: 'complete',
        updated_at: '2026-02-09T14:30:00Z',
      });
      renderPage();

      await waitFor(() => {
        expect(screen.getByText(/Generated.*ago/)).toBeInTheDocument();
      });

      const timestampEl = screen.getByTitle('2026-02-09T14:30:00Z');
      expect(timestampEl).toBeInTheDocument();
    });

    it('shows Regenerate button when resume exists', async () => {
      vi.mocked(applicationsApi.getApplication).mockResolvedValue({
        ...mockReviewedApp,
        resume_content: '# Resume',
        generation_status: 'complete',
      });
      renderPage();

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /regenerate/i })).toBeInTheDocument();
      });
    });

    it('shows confirmation dialog on Regenerate click', async () => {
      const user = userEvent.setup();
      vi.mocked(applicationsApi.getApplication).mockResolvedValue({
        ...mockReviewedApp,
        resume_content: '# Resume',
        generation_status: 'complete',
      });
      renderPage();

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /regenerate/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /regenerate/i }));

      await waitFor(() => {
        expect(screen.getByText('Regenerate Resume?')).toBeInTheDocument();
      });
    });

    it('calls generateResume after confirming regeneration', async () => {
      const user = userEvent.setup();
      vi.mocked(applicationsApi.getApplication).mockResolvedValue({
        ...mockReviewedApp,
        resume_content: '# Resume',
        generation_status: 'complete',
      });
      vi.mocked(generationApi.generateResume).mockResolvedValue({
        message: 'Resume generated successfully',
        resume_content: '# New Resume',
        status: 'complete',
      });
      renderPage();

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /regenerate/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /regenerate/i }));

      await waitFor(() => {
        expect(screen.getByText('Regenerate Resume?')).toBeInTheDocument();
      });

      // Click the confirm "Regenerate" button in the dialog
      const dialogButtons = screen.getAllByRole('button', { name: /regenerate/i });
      const confirmButton = dialogButtons[dialogButtons.length - 1];
      await user.click(confirmButton);

      await waitFor(() => {
        expect(generationApi.generateResume).toHaveBeenCalledWith(1);
      });
    });
  });

  describe('error handling', () => {
    it('shows error message when generation fails', async () => {
      const user = userEvent.setup();
      vi.mocked(applicationsApi.getApplication).mockResolvedValue(mockReviewedApp);
      vi.mocked(generationApi.generateResume).mockRejectedValue(
        new Error('LLM service unavailable'),
      );
      renderPage();

      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Generate Resume' })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: 'Generate Resume' }));

      await waitFor(() => {
        expect(screen.getByText('Generation failed')).toBeInTheDocument();
        expect(screen.getByText('LLM service unavailable')).toBeInTheDocument();
      });
    });

    it('shows Try Again button after error', async () => {
      const user = userEvent.setup();
      vi.mocked(applicationsApi.getApplication).mockResolvedValue(mockReviewedApp);
      vi.mocked(generationApi.generateResume).mockRejectedValue(
        new Error('Service error'),
      );
      renderPage();

      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Generate Resume' })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: 'Generate Resume' }));

      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Try Again' })).toBeInTheDocument();
      });
    });
  });
});
