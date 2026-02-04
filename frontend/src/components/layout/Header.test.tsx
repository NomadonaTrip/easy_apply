import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Header } from './Header';
import { useAuthStore } from '@/stores/authStore';
import * as rolesApi from '@/api/roles';

// Mock the roles API
vi.mock('@/api/roles', () => ({
  getRoles: vi.fn(),
  createRole: vi.fn(),
  deleteRole: vi.fn(),
}));

// Mock queryClient for roleStore
vi.mock('@/lib/queryClient', () => ({
  queryClient: {
    invalidateQueries: vi.fn(),
    clear: vi.fn(),
  },
}));

const mockUser = {
  id: 1,
  username: 'testuser',
  created_at: '2026-02-03T00:00:00Z',
};

const mockRoles = [
  { id: 1, user_id: 1, name: 'Software Engineer', created_at: '2026-02-03T00:00:00Z' },
  { id: 2, user_id: 1, name: 'Product Manager', created_at: '2026-02-03T00:00:00Z' },
];

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>{children}</MemoryRouter>
      </QueryClientProvider>
    );
  };
}

describe('Header', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      isLoggingOut: false,
      logoutError: null,
    });
  });

  it('should display app name', () => {
    render(<Header />, { wrapper: createWrapper() });

    expect(screen.getByText('easy_apply')).toBeInTheDocument();
  });

  it('should not show RoleSelector when user is not authenticated', () => {
    useAuthStore.setState({
      user: null,
      isAuthenticated: false,
    });
    vi.mocked(rolesApi.getRoles).mockResolvedValue([]);

    render(<Header />, { wrapper: createWrapper() });

    expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
  });

  it('should show RoleSelector when user is authenticated', async () => {
    useAuthStore.setState({
      user: mockUser,
      isAuthenticated: true,
    });
    vi.mocked(rolesApi.getRoles).mockResolvedValue(mockRoles);

    render(<Header />, { wrapper: createWrapper() });

    // Wait for RoleSelector to render
    await waitFor(() => {
      // Either combobox (if roles loaded) or loading skeleton should be present
      const combobox = screen.queryByRole('combobox');
      const skeleton = document.querySelector('.animate-pulse');
      expect(combobox || skeleton).toBeTruthy();
    });
  });

  it('should display username when authenticated', () => {
    useAuthStore.setState({
      user: mockUser,
      isAuthenticated: true,
    });
    vi.mocked(rolesApi.getRoles).mockResolvedValue([]);

    render(<Header />, { wrapper: createWrapper() });

    expect(screen.getByText('testuser')).toBeInTheDocument();
  });

  it('should display logout button when authenticated', () => {
    useAuthStore.setState({
      user: mockUser,
      isAuthenticated: true,
    });
    vi.mocked(rolesApi.getRoles).mockResolvedValue([]);

    render(<Header />, { wrapper: createWrapper() });

    expect(screen.getByRole('button', { name: /logout/i })).toBeInTheDocument();
  });

  it('should not display user controls when not authenticated', () => {
    useAuthStore.setState({
      user: null,
      isAuthenticated: false,
    });

    render(<Header />, { wrapper: createWrapper() });

    expect(screen.queryByText('testuser')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /logout/i })).not.toBeInTheDocument();
  });
});
