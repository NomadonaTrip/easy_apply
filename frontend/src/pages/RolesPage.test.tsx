import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RolesPage } from './RolesPage';
import * as rolesApi from '@/api/roles';

// Mock the roles API
vi.mock('@/api/roles', () => ({
  getRoles: vi.fn(),
  createRole: vi.fn(),
  deleteRole: vi.fn(),
}));

function renderRolesPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <RolesPage />
    </QueryClientProvider>
  );
}

describe('RolesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('loading state', () => {
    it('should show loading message while fetching roles', () => {
      vi.mocked(rolesApi.getRoles).mockImplementation(
        () => new Promise(() => {})
      );

      renderRolesPage();

      expect(screen.getByText(/loading roles/i)).toBeInTheDocument();
    });
  });

  describe('error state', () => {
    it('should show error message when fetch fails', async () => {
      vi.mocked(rolesApi.getRoles).mockRejectedValueOnce(new Error('Network error'));

      renderRolesPage();

      await waitFor(() => {
        expect(screen.getByText(/failed to load roles/i)).toBeInTheDocument();
      });
    });
  });

  describe('empty state', () => {
    it('should show empty state when no roles exist', async () => {
      vi.mocked(rolesApi.getRoles).mockResolvedValueOnce([]);

      renderRolesPage();

      await waitFor(() => {
        expect(screen.getByText(/create your first role to get started/i)).toBeInTheDocument();
      });
    });
  });

  describe('roles list', () => {
    it('should display list of roles', async () => {
      const mockRoles = [
        { id: 1, user_id: 1, name: 'Product Manager', created_at: '2026-01-01' },
        { id: 2, user_id: 1, name: 'Business Analyst', created_at: '2026-01-02' },
      ];
      vi.mocked(rolesApi.getRoles).mockResolvedValueOnce(mockRoles);

      renderRolesPage();

      await waitFor(() => {
        expect(screen.getByText('Product Manager')).toBeInTheDocument();
        expect(screen.getByText('Business Analyst')).toBeInTheDocument();
      });
    });

    it('should render delete button for each role', async () => {
      const mockRoles = [
        { id: 1, user_id: 1, name: 'Product Manager', created_at: '2026-01-01' },
      ];
      vi.mocked(rolesApi.getRoles).mockResolvedValueOnce(mockRoles);

      renderRolesPage();

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /delete product manager/i })).toBeInTheDocument();
      });
    });
  });

  describe('role creation', () => {
    it('should render the role create form', async () => {
      vi.mocked(rolesApi.getRoles).mockResolvedValueOnce([]);

      renderRolesPage();

      await waitFor(() => {
        expect(screen.getByLabelText(/role name/i)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /add role/i })).toBeInTheDocument();
      });
    });

    it('should create a role when form is submitted', async () => {
      const mockRoles = [{ id: 1, user_id: 1, name: 'Product Manager', created_at: '2026-01-01' }];
      vi.mocked(rolesApi.getRoles).mockResolvedValue([]);
      vi.mocked(rolesApi.createRole).mockResolvedValueOnce(mockRoles[0]);

      renderRolesPage();

      await waitFor(() => {
        expect(screen.getByLabelText(/role name/i)).toBeInTheDocument();
      });

      fireEvent.change(screen.getByLabelText(/role name/i), {
        target: { value: 'Product Manager' },
      });
      fireEvent.click(screen.getByRole('button', { name: /add role/i }));

      await waitFor(() => {
        expect(rolesApi.createRole).toHaveBeenCalledWith({ name: 'Product Manager' });
      });
    });
  });

  describe('role deletion', () => {
    it('should call deleteRole API when delete button is clicked', async () => {
      const mockRoles = [
        { id: 1, user_id: 1, name: 'Product Manager', created_at: '2026-01-01' },
      ];
      vi.mocked(rolesApi.getRoles).mockResolvedValue(mockRoles);
      vi.mocked(rolesApi.deleteRole).mockResolvedValueOnce(undefined);

      renderRolesPage();

      await waitFor(() => {
        expect(screen.getByText('Product Manager')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole('button', { name: /delete product manager/i }));

      await waitFor(() => {
        expect(rolesApi.deleteRole).toHaveBeenCalledWith(1);
      });
    });

    it('should display error message when delete fails', async () => {
      const mockRoles = [
        { id: 1, user_id: 1, name: 'Product Manager', created_at: '2026-01-01' },
      ];
      vi.mocked(rolesApi.getRoles).mockResolvedValue(mockRoles);
      vi.mocked(rolesApi.deleteRole).mockRejectedValueOnce(new Error('Server error'));

      renderRolesPage();

      await waitFor(() => {
        expect(screen.getByText('Product Manager')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole('button', { name: /delete product manager/i }));

      await waitFor(() => {
        expect(screen.getByText(/failed to delete role/i)).toBeInTheDocument();
      });
    });
  });

  describe('page structure', () => {
    it('should render page title', async () => {
      vi.mocked(rolesApi.getRoles).mockResolvedValueOnce([]);

      renderRolesPage();

      await waitFor(() => {
        expect(screen.getByRole('heading', { name: /manage roles/i })).toBeInTheDocument();
      });
    });

    it('should render Add New Role card', async () => {
      vi.mocked(rolesApi.getRoles).mockResolvedValueOnce([]);

      renderRolesPage();

      await waitFor(() => {
        expect(screen.getByText('Add New Role')).toBeInTheDocument();
      });
    });

    it('should render Your Roles card', async () => {
      vi.mocked(rolesApi.getRoles).mockResolvedValueOnce([]);

      renderRolesPage();

      await waitFor(() => {
        expect(screen.getByText('Your Roles')).toBeInTheDocument();
      });
    });
  });
});
