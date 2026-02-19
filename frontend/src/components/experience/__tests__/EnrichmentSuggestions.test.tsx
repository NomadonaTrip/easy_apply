/* eslint-disable @typescript-eslint/no-explicit-any */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { EnrichmentSuggestions } from '../EnrichmentSuggestions';

// Mock the hooks
vi.mock('@/hooks/useExperience', () => ({
  useEnrichmentCandidates: vi.fn(),
  useAcceptCandidate: vi.fn(),
  useDismissCandidate: vi.fn(),
  useBulkResolve: vi.fn(),
}));

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

import {
  useEnrichmentCandidates,
  useAcceptCandidate,
  useDismissCandidate,
  useBulkResolve,
} from '@/hooks/useExperience';

const mockUseEnrichmentCandidates = vi.mocked(useEnrichmentCandidates);
const mockUseAcceptCandidate = vi.mocked(useAcceptCandidate);
const mockUseDismissCandidate = vi.mocked(useDismissCandidate);
const mockUseBulkResolve = vi.mocked(useBulkResolve);

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

const mockAcceptMutate = vi.fn();
const mockDismissMutate = vi.fn();
const mockBulkMutate = vi.fn();

beforeEach(() => {
  mockUseAcceptCandidate.mockReturnValue({
    mutate: mockAcceptMutate,
    isPending: false,
  } as any);
  mockUseDismissCandidate.mockReturnValue({
    mutate: mockDismissMutate,
    isPending: false,
  } as any);
  mockUseBulkResolve.mockReturnValue({
    mutate: mockBulkMutate,
    isPending: false,
  } as any);
});

describe('EnrichmentSuggestions', () => {
  it('renders loading skeleton when loading', () => {
    mockUseEnrichmentCandidates.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      refetch: vi.fn(),
    } as any);

    render(<EnrichmentSuggestions />, { wrapper: createWrapper() });

    // Skeleton elements should be present (Card with Skeleton children)
    const skeletons = document.querySelectorAll('[class*="animate-pulse"], [class*="skeleton"]');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('renders error state with retry button', () => {
    const mockRefetch = vi.fn();
    mockUseEnrichmentCandidates.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Network error'),
      refetch: mockRefetch,
    } as any);

    render(<EnrichmentSuggestions />, { wrapper: createWrapper() });

    expect(screen.getByText('Failed to load enrichment suggestions.')).toBeInTheDocument();
    expect(screen.getByText('Retry')).toBeInTheDocument();
  });

  it('renders empty state when no pending candidates', () => {
    mockUseEnrichmentCandidates.mockReturnValue({
      data: { candidates: {}, total_pending: 0 },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    render(<EnrichmentSuggestions />, { wrapper: createWrapper() });

    expect(screen.getByText('Your experience database is up to date.')).toBeInTheDocument();
  });

  it('renders candidates grouped by application with company name', () => {
    mockUseEnrichmentCandidates.mockReturnValue({
      data: {
        candidates: {
          '1': {
            company_name: 'Acme Corp',
            candidates: [
              {
                id: 10,
                role_id: 1,
                application_id: 1,
                document_type: 'resume',
                candidate_type: 'skill',
                name: 'Kubernetes',
                category: 'DevOps',
                context: null,
                status: 'pending',
                created_at: '2024-01-01T00:00:00Z',
                resolved_at: null,
              },
              {
                id: 11,
                role_id: 1,
                application_id: 1,
                document_type: 'resume',
                candidate_type: 'accomplishment',
                name: 'Led migration to microservices',
                category: null,
                context: 'At TechCo',
                status: 'pending',
                created_at: '2024-01-01T00:00:00Z',
                resolved_at: null,
              },
            ],
          },
        },
        total_pending: 2,
      },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    render(<EnrichmentSuggestions />, { wrapper: createWrapper() });

    // Check heading with count
    expect(screen.getByText('Suggestions (2 pending)')).toBeInTheDocument();

    // Check company name
    expect(screen.getByText('Acme Corp')).toBeInTheDocument();

    // Check candidate names
    expect(screen.getByText('Kubernetes')).toBeInTheDocument();
    expect(screen.getByText('Led migration to microservices')).toBeInTheDocument();

    // Check type badges
    expect(screen.getByText('Skill')).toBeInTheDocument();
    expect(screen.getByText('Accomplishment')).toBeInTheDocument();

    // Check context
    expect(screen.getByText('At TechCo')).toBeInTheDocument();

    // Check bulk action buttons
    expect(screen.getByText('Accept All (2)')).toBeInTheDocument();
    expect(screen.getByText('Dismiss All (2)')).toBeInTheDocument();
  });

  it('calls accept mutation when accept button clicked', async () => {
    const user = userEvent.setup();

    mockUseEnrichmentCandidates.mockReturnValue({
      data: {
        candidates: {
          '1': {
            company_name: 'Test Co',
            candidates: [
              {
                id: 42,
                role_id: 1,
                application_id: 1,
                document_type: 'resume',
                candidate_type: 'skill',
                name: 'Terraform',
                category: 'IaC',
                context: null,
                status: 'pending',
                created_at: '2024-01-01T00:00:00Z',
                resolved_at: null,
              },
            ],
          },
        },
        total_pending: 1,
      },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    render(<EnrichmentSuggestions />, { wrapper: createWrapper() });

    const acceptButton = screen.getByLabelText('Accept Terraform');
    await user.click(acceptButton);

    expect(mockAcceptMutate).toHaveBeenCalledWith(42, expect.objectContaining({
      onSuccess: expect.any(Function),
      onError: expect.any(Function),
    }));
  });

  it('calls dismiss mutation when dismiss button clicked', async () => {
    const user = userEvent.setup();

    mockUseEnrichmentCandidates.mockReturnValue({
      data: {
        candidates: {
          '1': {
            company_name: 'Test Co',
            candidates: [
              {
                id: 42,
                role_id: 1,
                application_id: 1,
                document_type: 'resume',
                candidate_type: 'skill',
                name: 'Terraform',
                category: 'IaC',
                context: null,
                status: 'pending',
                created_at: '2024-01-01T00:00:00Z',
                resolved_at: null,
              },
            ],
          },
        },
        total_pending: 1,
      },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    render(<EnrichmentSuggestions />, { wrapper: createWrapper() });

    const dismissButton = screen.getByLabelText('Dismiss Terraform');
    await user.click(dismissButton);

    expect(mockDismissMutate).toHaveBeenCalledWith(42, expect.objectContaining({
      onSuccess: expect.any(Function),
      onError: expect.any(Function),
    }));
  });

  it('calls bulk accept when Accept All clicked', async () => {
    const user = userEvent.setup();

    const candidates = [
      {
        id: 10,
        role_id: 1,
        application_id: 1,
        document_type: 'resume',
        candidate_type: 'skill',
        name: 'Go',
        category: 'Language',
        context: null,
        status: 'pending',
        created_at: '2024-01-01T00:00:00Z',
        resolved_at: null,
      },
      {
        id: 11,
        role_id: 1,
        application_id: 1,
        document_type: 'resume',
        candidate_type: 'skill',
        name: 'Rust',
        category: 'Language',
        context: null,
        status: 'pending',
        created_at: '2024-01-01T00:00:00Z',
        resolved_at: null,
      },
    ];

    mockUseEnrichmentCandidates.mockReturnValue({
      data: {
        candidates: { '1': { company_name: 'Test Co', candidates } },
        total_pending: 2,
      },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    render(<EnrichmentSuggestions />, { wrapper: createWrapper() });

    const acceptAllBtn = screen.getByText('Accept All (2)');
    await user.click(acceptAllBtn);

    expect(mockBulkMutate).toHaveBeenCalledWith(
      { ids: [10, 11], action: 'accept' },
      expect.objectContaining({
        onSuccess: expect.any(Function),
        onError: expect.any(Function),
      }),
    );
  });

  it('renders retry button on error and calls refetch', async () => {
    const user = userEvent.setup();
    const mockRefetch = vi.fn();

    mockUseEnrichmentCandidates.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Server error'),
      refetch: mockRefetch,
    } as any);

    render(<EnrichmentSuggestions />, { wrapper: createWrapper() });

    const retryBtn = screen.getByText('Retry');
    await user.click(retryBtn);

    expect(mockRefetch).toHaveBeenCalled();
  });
});
