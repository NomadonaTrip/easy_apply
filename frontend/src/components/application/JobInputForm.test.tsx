import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { JobInputForm } from './JobInputForm';

describe('JobInputForm', () => {
  describe('rendering', () => {
    it('renders company name and job description fields', () => {
      render(<JobInputForm onSubmit={vi.fn()} />);

      expect(screen.getByLabelText(/company name/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/job description/i)).toBeInTheDocument();
    });

    it('renders job URL optional field', () => {
      render(<JobInputForm onSubmit={vi.fn()} />);

      expect(screen.getByLabelText(/job url/i)).toBeInTheDocument();
    });

    it('renders submit button', () => {
      render(<JobInputForm onSubmit={vi.fn()} />);

      expect(screen.getByRole('button', { name: /create application/i })).toBeInTheDocument();
    });
  });

  describe('validation', () => {
    it('shows validation error for empty company name', async () => {
      render(<JobInputForm onSubmit={vi.fn()} />);

      fireEvent.click(screen.getByRole('button', { name: /create/i }));

      await waitFor(() => {
        expect(screen.getByText(/company name is required/i)).toBeInTheDocument();
      });
    });

    it('shows validation error for short job description', async () => {
      render(<JobInputForm onSubmit={vi.fn()} />);

      fireEvent.change(screen.getByLabelText(/company name/i), { target: { value: 'Acme' } });
      fireEvent.change(screen.getByLabelText(/job description/i), { target: { value: 'short' } });
      fireEvent.click(screen.getByRole('button', { name: /create/i }));

      await waitFor(() => {
        expect(screen.getByText(/at least 10 characters/i)).toBeInTheDocument();
      });
    });

    it('does not call onSubmit when validation fails', async () => {
      const mockSubmit = vi.fn();
      render(<JobInputForm onSubmit={mockSubmit} />);

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
      render(<JobInputForm onSubmit={mockSubmit} />);

      fireEvent.change(screen.getByLabelText(/company name/i), { target: { value: 'Acme Corp' } });
      fireEvent.change(screen.getByLabelText(/job description/i), {
        target: { value: 'Looking for a senior product manager with 5+ years experience...' },
      });
      fireEvent.click(screen.getByRole('button', { name: /create/i }));

      await waitFor(() => {
        expect(mockSubmit).toHaveBeenCalledWith(
          expect.objectContaining({
            company_name: 'Acme Corp',
            job_posting: 'Looking for a senior product manager with 5+ years experience...',
          }),
          expect.anything(),
        );
      });
    });
  });

  describe('loading state', () => {
    it('disables submit button when loading', () => {
      render(<JobInputForm onSubmit={vi.fn()} isLoading />);

      expect(screen.getByRole('button', { name: /creating/i })).toBeDisabled();
    });

    it('shows "Creating..." text when loading', () => {
      render(<JobInputForm onSubmit={vi.fn()} isLoading />);

      expect(screen.getByRole('button')).toHaveTextContent('Creating...');
    });
  });

  describe('accessibility', () => {
    it('sets aria-invalid on company name when validation fails', async () => {
      render(<JobInputForm onSubmit={vi.fn()} />);

      fireEvent.click(screen.getByRole('button', { name: /create/i }));

      await waitFor(() => {
        expect(screen.getByLabelText(/company name/i)).toHaveAttribute('aria-invalid', 'true');
      });
    });
  });
});
