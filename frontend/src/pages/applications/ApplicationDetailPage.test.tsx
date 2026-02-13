import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClientProvider, QueryClient } from '@tanstack/react-query';
import { ApplicationDetailPage } from './ApplicationDetailPage';
import { TooltipProvider } from '@/components/ui/tooltip';
import * as applicationsApi from '@/api/applications';

// Mock react-router-dom's useParams
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useParams: () => ({ id: '1' }),
  };
});

// Mock the API
vi.mock('@/api/applications');

const mockApplication: applicationsApi.Application = {
  id: 1,
  role_id: 1,
  company_name: 'Acme Corp',
  job_posting: 'Senior Developer needed',
  job_url: 'https://example.com/job',
  status: 'keywords',
  keywords: JSON.stringify([{ text: 'React', priority: 1, category: 'technical_skill' }]),
  research_data: null,
  manual_context: null,
  generation_status: 'idle',
  resume_content: null,
  cover_letter_content: null,
  cover_letter_tone: null,
  resume_violations_fixed: null,
  resume_constraint_warnings: null,
  cover_letter_violations_fixed: null,
  cover_letter_constraint_warnings: null,
  created_at: '2026-02-01T10:00:00Z',
  updated_at: '2026-02-02T15:30:00Z',
};

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <TooltipProvider>
          <ApplicationDetailPage />
        </TooltipProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

describe('ApplicationDetailPage', () => {
  beforeEach(() => {
    vi.mocked(applicationsApi.getApplication).mockResolvedValue(mockApplication);
  });

  it('displays the company name', async () => {
    renderPage();
    expect(await screen.findByText('Acme Corp')).toBeInTheDocument();
  });

  it('displays creation date', async () => {
    renderPage();
    // Should show creation time info - the date is in a span with title attribute
    const dateSpan = await screen.findByTitle('2026-02-01T10:00:00Z');
    expect(dateSpan).toBeInTheDocument();
    expect(dateSpan.textContent).toMatch(/Created .+ ago/);
  });

  it('displays current status badge', async () => {
    renderPage();
    // The badge has a tooltip-trigger data-slot attribute
    const badge = await screen.findByText('Keywords', { selector: '[data-slot="tooltip-trigger"]' });
    expect(badge).toBeInTheDocument();
  });

  it('displays the wizard step indicator', async () => {
    renderPage();
    // WizardStepLayout shows step labels on desktop; in jsdom both mobile and desktop render
    expect(await screen.findByText('Input')).toBeInTheDocument();
    expect(screen.getByText('Research')).toBeInTheDocument();
  });

  it('displays loading state with skeletons', () => {
    vi.mocked(applicationsApi.getApplication).mockReturnValue(new Promise(() => {}));
    renderPage();
    const skeletons = document.querySelectorAll('[data-slot="skeleton"]');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('displays not found with back link when application is null', async () => {
    vi.mocked(applicationsApi.getApplication).mockResolvedValue(null as unknown as applicationsApi.Application);
    renderPage();
    expect(await screen.findByText('Application not found')).toBeInTheDocument();
    const backLink = screen.getByRole('link', { name: /back to dashboard/i });
    expect(backLink).toHaveAttribute('href', '/dashboard');
  });

  it('displays job posting content', async () => {
    renderPage();
    expect(await screen.findByText('Senior Developer needed')).toBeInTheDocument();
  });

  it('displays link to original posting when job_url exists', async () => {
    renderPage();
    const link = await screen.findByRole('link', { name: /view original posting/i });
    expect(link).toHaveAttribute('href', 'https://example.com/job');
  });

  it('displays extracted keywords', async () => {
    renderPage();
    expect(await screen.findByText('React')).toBeInTheDocument();
  });

  it('handles malformed keywords JSON gracefully', async () => {
    vi.mocked(applicationsApi.getApplication).mockResolvedValue({
      ...mockApplication,
      keywords: 'invalid-json{{{',
    });
    renderPage();
    // Page should still render without crashing
    expect(await screen.findByText('Acme Corp')).toBeInTheDocument();
  });

  describe('navigation links', () => {
    it('displays a "Back to Dashboard" link pointing to /dashboard', async () => {
      renderPage();
      const backLink = await screen.findByRole('link', { name: /back to dashboard/i });
      expect(backLink).toHaveAttribute('href', '/dashboard');
    });

    it('displays a "View Keywords" link in the keywords card when keywords exist', async () => {
      renderPage();
      const viewKeywordsLink = await screen.findByRole('link', { name: /view keywords/i });
      expect(viewKeywordsLink).toHaveAttribute('href', '/applications/1/keywords');
    });

    it('displays a standalone "View Keywords" link when no keywords exist', async () => {
      vi.mocked(applicationsApi.getApplication).mockResolvedValue({
        ...mockApplication,
        keywords: null,
      });
      renderPage();
      const viewKeywordsLink = await screen.findByRole('link', { name: /view keywords/i });
      expect(viewKeywordsLink).toHaveAttribute('href', '/applications/1/keywords');
    });

    it('still displays the "Continue Workflow" button', async () => {
      renderPage();
      expect(await screen.findByRole('button', { name: /continue workflow/i })).toBeInTheDocument();
    });

    it('hides "Continue Workflow" button for terminal statuses', async () => {
      vi.mocked(applicationsApi.getApplication).mockResolvedValue({
        ...mockApplication,
        status: 'sent' as applicationsApi.ApplicationStatus,
      });
      renderPage();
      await screen.findByText('Acme Corp');
      expect(screen.queryByRole('button', { name: /continue workflow/i })).not.toBeInTheDocument();
    });
  });
});
