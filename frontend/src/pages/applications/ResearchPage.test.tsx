import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ResearchPage } from './ResearchPage';

// Mock the hooks and API
vi.mock('@/hooks/useResearchStream', () => ({
  RESEARCH_CATEGORIES: [
    { source: 'strategic_initiatives', label: 'Strategic Initiatives' },
    { source: 'competitive_landscape', label: 'Competitive Landscape' },
    { source: 'news_momentum', label: 'Recent News & Momentum' },
    { source: 'industry_context', label: 'Industry Context' },
    { source: 'culture_values', label: 'Culture & Values' },
    { source: 'leadership_direction', label: 'Leadership Direction' },
  ],
  useResearchStream: vi.fn(() => ({
    sources: [
      { source: 'strategic_initiatives', status: 'pending' },
      { source: 'competitive_landscape', status: 'pending' },
      { source: 'news_momentum', status: 'pending' },
      { source: 'industry_context', status: 'pending' },
      { source: 'culture_values', status: 'pending' },
      { source: 'leadership_direction', status: 'pending' },
    ],
    isComplete: false,
    isError: false,
    error: null,
    progress: 0,
    startResearch: vi.fn(),
    retryConnection: vi.fn(),
  })),
}));

vi.mock('@/api/applications', () => ({
  getApplication: vi.fn(() =>
    Promise.resolve({
      id: 1,
      role_id: 1,
      company_name: 'Acme Corp',
      job_posting: 'Software Engineer',
      status: 'keywords',
    }),
  ),
}));

vi.mock('@/stores/roleStore', () => ({
  useRoleStore: {
    getState: () => ({ currentRole: { id: 1 } }),
  },
}));

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
}

function renderPage() {
  const queryClient = createQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/applications/1/research']}>
        <Routes>
          <Route path="/applications/:id/research" element={<ResearchPage />} />
          <Route path="/applications/:id/keywords" element={<div>Keywords Page</div>} />
          <Route path="/applications/:id/review" element={<div>Review Page</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('ResearchPage', () => {
  it('renders wizard step indicator at step 3', async () => {
    renderPage();
    expect(await screen.findByText('Research')).toBeInTheDocument();
  });

  it('displays company name in card title', async () => {
    renderPage();
    expect(await screen.findByText('Researching Acme Corp')).toBeInTheDocument();
  });

  it('renders all 6 research categories', async () => {
    renderPage();
    expect(await screen.findByText('Strategic Initiatives')).toBeInTheDocument();
    expect(screen.getByText('Competitive Landscape')).toBeInTheDocument();
    expect(screen.getByText('Recent News & Momentum')).toBeInTheDocument();
    expect(screen.getByText('Industry Context')).toBeInTheDocument();
    expect(screen.getByText('Culture & Values')).toBeInTheDocument();
    expect(screen.getByText('Leadership Direction')).toBeInTheDocument();
  });

  it('renders progress bar showing 0/6 categories', async () => {
    renderPage();
    expect(await screen.findByText('0/6 categories')).toBeInTheDocument();
  });

  it('renders back button', async () => {
    renderPage();
    expect(await screen.findByRole('button', { name: /back/i })).toBeInTheDocument();
  });

  it('shows error alert with retry button when error occurs', async () => {
    const { useResearchStream } = await import('@/hooks/useResearchStream');
    vi.mocked(useResearchStream).mockReturnValue({
      sources: [
        { source: 'strategic_initiatives', status: 'pending' },
        { source: 'competitive_landscape', status: 'pending' },
        { source: 'news_momentum', status: 'pending' },
        { source: 'industry_context', status: 'pending' },
        { source: 'culture_values', status: 'pending' },
        { source: 'leadership_direction', status: 'pending' },
      ],
      isComplete: false,
      isError: true,
      error: 'Connection lost. Click retry to reconnect.',
      progress: 0,
      startResearch: vi.fn(),
      retryConnection: vi.fn(),
    });

    renderPage();
    expect(await screen.findByText('Connection lost. Click retry to reconnect.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
  });

  it('shows complete state with continue button', async () => {
    const { useResearchStream } = await import('@/hooks/useResearchStream');
    vi.mocked(useResearchStream).mockReturnValue({
      sources: [
        { source: 'strategic_initiatives', status: 'complete', found: true },
        { source: 'competitive_landscape', status: 'complete', found: true },
        { source: 'news_momentum', status: 'complete', found: true },
        { source: 'industry_context', status: 'complete', found: true },
        { source: 'culture_values', status: 'complete', found: true },
        { source: 'leadership_direction', status: 'complete', found: true },
      ],
      isComplete: true,
      isError: false,
      error: null,
      progress: 100,
      startResearch: vi.fn(),
      retryConnection: vi.fn(),
    });

    renderPage();
    expect(await screen.findByText('Research Complete')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /continue to review/i })).toBeInTheDocument();
  });

  it('shows gap warning when some sources failed', async () => {
    const { useResearchStream } = await import('@/hooks/useResearchStream');
    vi.mocked(useResearchStream).mockReturnValue({
      sources: [
        { source: 'strategic_initiatives', status: 'complete', found: true },
        { source: 'competitive_landscape', status: 'complete', found: true },
        { source: 'news_momentum', status: 'failed', found: false },
        { source: 'industry_context', status: 'complete', found: true },
        { source: 'culture_values', status: 'complete', found: true },
        { source: 'leadership_direction', status: 'failed', found: false },
      ],
      isComplete: true,
      isError: false,
      error: null,
      progress: 100,
      startResearch: vi.fn(),
      retryConnection: vi.fn(),
    });

    renderPage();
    expect(await screen.findByText(/some sources had limited information/i)).toBeInTheDocument();
  });
});
