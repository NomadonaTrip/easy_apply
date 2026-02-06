import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { JobInputForm } from './JobInputForm';

// Mock the useScrape hook
const mockMutateAsync = vi.fn();
const mockReset = vi.fn();
let mockScrapeState = {
  mutateAsync: mockMutateAsync,
  isPending: false,
  isError: false,
  error: null as { message: string } | null,
  reset: mockReset,
};

vi.mock('@/hooks/useScrape', () => ({
  useScrapeJobPosting: () => mockScrapeState,
}));

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
  );
}

describe('JobInputForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockScrapeState = {
      mutateAsync: mockMutateAsync,
      isPending: false,
      isError: false,
      error: null,
      reset: mockReset,
    };
  });

  describe('rendering', () => {
    it('renders company name and job description fields', () => {
      renderWithProviders(<JobInputForm onSubmit={vi.fn()} />);

      expect(screen.getByLabelText(/company name/i)).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/paste the full job description/i)).toBeInTheDocument();
    });

    it('renders submit button', () => {
      renderWithProviders(<JobInputForm onSubmit={vi.fn()} />);

      expect(screen.getByRole('button', { name: /create application/i })).toBeInTheDocument();
    });

    it('renders paste and URL tabs', () => {
      renderWithProviders(<JobInputForm onSubmit={vi.fn()} />);

      expect(screen.getByRole('tab', { name: /paste text/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /from url/i })).toBeInTheDocument();
    });
  });

  describe('validation', () => {
    it('shows validation error for empty company name', async () => {
      renderWithProviders(<JobInputForm onSubmit={vi.fn()} />);

      fireEvent.click(screen.getByRole('button', { name: /create/i }));

      await waitFor(() => {
        expect(screen.getByText(/company name is required/i)).toBeInTheDocument();
      });
    });

    it('shows validation error for short job description', async () => {
      renderWithProviders(<JobInputForm onSubmit={vi.fn()} />);

      fireEvent.change(screen.getByLabelText(/company name/i), { target: { value: 'Acme' } });
      fireEvent.change(screen.getByPlaceholderText(/paste the full job description/i), {
        target: { value: 'short' },
      });
      fireEvent.click(screen.getByRole('button', { name: /create/i }));

      await waitFor(() => {
        expect(screen.getByText(/at least 10 characters/i)).toBeInTheDocument();
      });
    });

    it('does not call onSubmit when validation fails', async () => {
      const mockSubmit = vi.fn();
      renderWithProviders(<JobInputForm onSubmit={mockSubmit} />);

      fireEvent.click(screen.getByRole('button', { name: /create/i }));

      await waitFor(() => {
        expect(screen.getByText(/company name is required/i)).toBeInTheDocument();
      });

      expect(mockSubmit).not.toHaveBeenCalled();
    });
  });

  describe('form submission', () => {
    it('calls onSubmit with valid data', async () => {
      const mockSubmit = vi.fn();
      renderWithProviders(<JobInputForm onSubmit={mockSubmit} />);

      fireEvent.change(screen.getByLabelText(/company name/i), {
        target: { value: 'Acme Corp' },
      });
      fireEvent.change(screen.getByPlaceholderText(/paste the full job description/i), {
        target: {
          value: 'Looking for a senior product manager with 5+ years experience...',
        },
      });
      fireEvent.click(screen.getByRole('button', { name: /create/i }));

      await waitFor(() => {
        expect(mockSubmit).toHaveBeenCalledWith(
          expect.objectContaining({
            company_name: 'Acme Corp',
            job_posting: 'Looking for a senior product manager with 5+ years experience...',
          }),
        );
      });
    });
  });

  describe('loading state', () => {
    it('disables submit button when loading', () => {
      renderWithProviders(<JobInputForm onSubmit={vi.fn()} isLoading />);

      expect(screen.getByRole('button', { name: /creating/i })).toBeDisabled();
    });

    it('shows "Creating..." text when loading', () => {
      renderWithProviders(<JobInputForm onSubmit={vi.fn()} isLoading />);

      expect(screen.getByRole('button', { name: /creating/i })).toHaveTextContent('Creating...');
    });
  });

  describe('accessibility', () => {
    it('sets aria-invalid on company name when validation fails', async () => {
      renderWithProviders(<JobInputForm onSubmit={vi.fn()} />);

      fireEvent.click(screen.getByRole('button', { name: /create/i }));

      await waitFor(() => {
        expect(screen.getByLabelText(/company name/i)).toHaveAttribute('aria-invalid', 'true');
      });
    });
  });

  describe('URL mode', () => {
    it('switches between paste and URL modes', async () => {
      const user = userEvent.setup();
      renderWithProviders(<JobInputForm onSubmit={vi.fn()} />);

      await user.click(screen.getByRole('tab', { name: /from url/i }));

      expect(screen.getByPlaceholderText(/https:\/\/company\.com\/jobs/i)).toBeInTheDocument();
    });

    it('shows fetch button in URL mode', async () => {
      const user = userEvent.setup();
      renderWithProviders(<JobInputForm onSubmit={vi.fn()} />);

      await user.click(screen.getByRole('tab', { name: /from url/i }));

      expect(screen.getByRole('button', { name: /fetch/i })).toBeInTheDocument();
    });

    it('disables fetch button when URL is empty', async () => {
      const user = userEvent.setup();
      renderWithProviders(<JobInputForm onSubmit={vi.fn()} />);

      await user.click(screen.getByRole('tab', { name: /from url/i }));

      expect(screen.getByRole('button', { name: /fetch/i })).toBeDisabled();
    });

    it('enables fetch button when URL is entered', async () => {
      const user = userEvent.setup();
      renderWithProviders(<JobInputForm onSubmit={vi.fn()} />);

      await user.click(screen.getByRole('tab', { name: /from url/i }));

      const urlInput = screen.getByPlaceholderText(/https:\/\/company\.com\/jobs/i);
      await user.type(urlInput, 'https://example.com/job');

      expect(screen.getByRole('button', { name: /fetch/i })).not.toBeDisabled();
    });

    it('shows error and paste option on fetch failure', async () => {
      mockScrapeState = {
        ...mockScrapeState,
        isError: true,
        error: { message: 'Failed to fetch URL' },
      };

      const user = userEvent.setup();
      renderWithProviders(<JobInputForm onSubmit={vi.fn()} />);

      await user.click(screen.getByRole('tab', { name: /from url/i }));

      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText(/failed to fetch url/i)).toBeInTheDocument();
      expect(screen.getByText(/paste manually instead/i)).toBeInTheDocument();
    });

    it('switches to paste mode when "paste manually" is clicked', async () => {
      mockScrapeState = {
        ...mockScrapeState,
        isError: true,
        error: { message: 'Failed to fetch URL' },
      };

      const user = userEvent.setup();
      renderWithProviders(<JobInputForm onSubmit={vi.fn()} />);

      await user.click(screen.getByRole('tab', { name: /from url/i }));
      await user.click(screen.getByText(/paste manually instead/i));

      expect(mockReset).toHaveBeenCalled();
    });

    it('shows loading state during fetch', async () => {
      mockScrapeState = {
        ...mockScrapeState,
        isPending: true,
      };

      const user = userEvent.setup();
      renderWithProviders(<JobInputForm onSubmit={vi.fn()} />);

      await user.click(screen.getByRole('tab', { name: /from url/i }));

      expect(screen.getByText(/fetching/i)).toBeInTheDocument();
    });

    it('URL input has accessible label', async () => {
      const user = userEvent.setup();
      renderWithProviders(<JobInputForm onSubmit={vi.fn()} />);

      await user.click(screen.getByRole('tab', { name: /from url/i }));

      expect(screen.getByLabelText(/job posting url/i)).toBeInTheDocument();
    });
  });
});
