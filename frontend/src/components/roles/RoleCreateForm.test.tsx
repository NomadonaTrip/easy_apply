import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RoleCreateForm } from './RoleCreateForm';
import * as rolesApi from '@/api/roles';

// Mock the roles API
vi.mock('@/api/roles', () => ({
  createRole: vi.fn(),
}));

function renderRoleCreateForm() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <RoleCreateForm />
    </QueryClientProvider>
  );
}

describe('RoleCreateForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('rendering', () => {
    it('should render role name input', () => {
      renderRoleCreateForm();
      expect(screen.getByLabelText(/role name/i)).toBeInTheDocument();
    });

    it('should render submit button', () => {
      renderRoleCreateForm();
      expect(screen.getByRole('button', { name: /add role/i })).toBeInTheDocument();
    });

    it('should have placeholder text', () => {
      renderRoleCreateForm();
      expect(screen.getByPlaceholderText(/product manager/i)).toBeInTheDocument();
    });
  });

  describe('validation', () => {
    it('should show error when submitting empty name', async () => {
      renderRoleCreateForm();

      fireEvent.click(screen.getByRole('button', { name: /add role/i }));

      await waitFor(() => {
        expect(screen.getByText(/role name is required/i)).toBeInTheDocument();
      });

      // Should not call API
      expect(rolesApi.createRole).not.toHaveBeenCalled();
    });

    it('should show error when submitting whitespace-only name', async () => {
      renderRoleCreateForm();

      fireEvent.change(screen.getByLabelText(/role name/i), {
        target: { value: '   ' },
      });
      fireEvent.click(screen.getByRole('button', { name: /add role/i }));

      await waitFor(() => {
        expect(screen.getByText(/role name is required/i)).toBeInTheDocument();
      });

      expect(rolesApi.createRole).not.toHaveBeenCalled();
    });
  });

  describe('form submission', () => {
    it('should call createRole API with trimmed name', async () => {
      const mockRole = { id: 1, user_id: 1, name: 'Product Manager', created_at: '2026-01-01' };
      vi.mocked(rolesApi.createRole).mockResolvedValueOnce(mockRole);

      renderRoleCreateForm();

      fireEvent.change(screen.getByLabelText(/role name/i), {
        target: { value: '  Product Manager  ' },
      });
      fireEvent.click(screen.getByRole('button', { name: /add role/i }));

      await waitFor(() => {
        expect(rolesApi.createRole).toHaveBeenCalledWith({ name: 'Product Manager' });
      });
    });

    it('should clear input after successful submission', async () => {
      const mockRole = { id: 1, user_id: 1, name: 'Product Manager', created_at: '2026-01-01' };
      vi.mocked(rolesApi.createRole).mockResolvedValueOnce(mockRole);

      renderRoleCreateForm();

      const input = screen.getByLabelText(/role name/i);
      fireEvent.change(input, { target: { value: 'Product Manager' } });
      fireEvent.click(screen.getByRole('button', { name: /add role/i }));

      await waitFor(() => {
        expect(input).toHaveValue('');
      });
    });

    it('should disable button while submitting', async () => {
      vi.mocked(rolesApi.createRole).mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 100))
      );

      renderRoleCreateForm();

      fireEvent.change(screen.getByLabelText(/role name/i), {
        target: { value: 'Product Manager' },
      });
      fireEvent.click(screen.getByRole('button', { name: /add role/i }));

      expect(screen.getByRole('button')).toBeDisabled();
      expect(screen.getByRole('button')).toHaveTextContent(/creating/i);
    });

    it('should disable input while submitting', async () => {
      vi.mocked(rolesApi.createRole).mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 100))
      );

      renderRoleCreateForm();

      const input = screen.getByLabelText(/role name/i);
      fireEvent.change(input, { target: { value: 'Product Manager' } });
      fireEvent.click(screen.getByRole('button', { name: /add role/i }));

      expect(input).toBeDisabled();
    });
  });

  describe('error handling', () => {
    it('should display error message on API failure', async () => {
      vi.mocked(rolesApi.createRole).mockRejectedValueOnce(new Error('Server error'));

      renderRoleCreateForm();

      fireEvent.change(screen.getByLabelText(/role name/i), {
        target: { value: 'Product Manager' },
      });
      fireEvent.click(screen.getByRole('button', { name: /add role/i }));

      await waitFor(() => {
        expect(screen.getByText(/failed to create role/i)).toBeInTheDocument();
      });
    });

    it('should not clear input on API failure', async () => {
      vi.mocked(rolesApi.createRole).mockRejectedValueOnce(new Error('Server error'));

      renderRoleCreateForm();

      const input = screen.getByLabelText(/role name/i);
      fireEvent.change(input, { target: { value: 'Product Manager' } });
      fireEvent.click(screen.getByRole('button', { name: /add role/i }));

      await waitFor(() => {
        expect(screen.getByText(/failed to create role/i)).toBeInTheDocument();
      });

      expect(input).toHaveValue('Product Manager');
    });
  });
});
