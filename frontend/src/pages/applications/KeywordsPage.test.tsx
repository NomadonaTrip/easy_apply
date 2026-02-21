import { vi, describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { KeywordsPage } from './KeywordsPage';

vi.mock('@/hooks/useKeywords', () => ({
  useSaveKeywords: vi.fn(() => ({
    save: vi.fn(),
    isSaving: false,
    error: null,
  })),
}));

vi.mock('@/api/applications', () => ({
  getApplication: vi.fn(),
}));

import { getApplication } from '@/api/applications';

const mockApplication = {
  id: 1,
  role_id: 1,
  company_name: 'Test Corp',
  job_posting: 'Test posting',
  job_url: null,
  status: 'keywords',
  keywords: JSON.stringify([
    { text: 'Python', priority: 9, category: 'technical_skill' },
    { text: 'React', priority: 8, category: 'technical_skill' },
  ]),
  research_data: null,
  manual_context: null,
  generation_status: 'idle',
  resume_content: null,
  cover_letter_content: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/applications/1/keywords']}>
        <Routes>
          <Route path="/applications/:id/keywords" element={<KeywordsPage />} />
          <Route path="/applications/:id/research" element={<div>Research Page</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
});

describe('KeywordsPage', () => {
  it('shows loading state while fetching', () => {
    vi.mocked(getApplication).mockReturnValue(new Promise(() => {}));
    renderPage();

    expect(screen.queryByRole('heading', { name: 'Keywords' })).not.toBeInTheDocument();
  });

  it('shows error state when fetch fails', async () => {
    vi.mocked(getApplication).mockRejectedValue(new Error('Network error'));
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Failed to load application data')).toBeInTheDocument();
    });
  });

  it('renders keywords when data loads', async () => {
    vi.mocked(getApplication).mockResolvedValue(mockApplication);
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Python')).toBeInTheDocument();
      expect(screen.getByText('React')).toBeInTheDocument();
    });
  });

  it('renders continue button', async () => {
    vi.mocked(getApplication).mockResolvedValue(mockApplication);
    renderPage();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Start Research' })).toBeInTheDocument();
    });
  });

  it('does not show save indicator before any reorder', async () => {
    vi.mocked(getApplication).mockResolvedValue(mockApplication);
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Python')).toBeInTheDocument();
    });

    expect(screen.queryByText('Saved')).not.toBeInTheDocument();
    expect(screen.queryByText('Saving...')).not.toBeInTheDocument();
  });

  it('renders pattern_boosted keywords without error', async () => {
    const appWithBoostedKeywords = {
      ...mockApplication,
      keywords: JSON.stringify([
        { text: 'Python', priority: 9, category: 'technical_skill', pattern_boosted: true },
        { text: 'React', priority: 8, category: 'technical_skill', pattern_boosted: true },
        { text: 'Docker', priority: 6, category: 'tool', pattern_boosted: false },
      ]),
    };
    vi.mocked(getApplication).mockResolvedValue(appWithBoostedKeywords);
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Python')).toBeInTheDocument();
      expect(screen.getByText('React')).toBeInTheDocument();
      expect(screen.getByText('Docker')).toBeInTheDocument();
    });
  });

  it('shows pattern boost alert when boosted keywords exist', async () => {
    const appWithBoostedKeywords = {
      ...mockApplication,
      keywords: JSON.stringify([
        { text: 'Python', priority: 9, category: 'technical_skill', pattern_boosted: true },
        { text: 'React', priority: 8, category: 'technical_skill', pattern_boosted: true },
        { text: 'Docker', priority: 6, category: 'tool', pattern_boosted: false },
      ]),
    };
    vi.mocked(getApplication).mockResolvedValue(appWithBoostedKeywords);
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Learning from your success')).toBeInTheDocument();
      expect(screen.getByText(/2 keywords? boosted/)).toBeInTheDocument();
    });
  });

  it('does not show pattern boost alert when no keywords are boosted', async () => {
    vi.mocked(getApplication).mockResolvedValue(mockApplication);
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Python')).toBeInTheDocument();
    });

    expect(screen.queryByText('Learning from your success')).not.toBeInTheDocument();
  });
});
