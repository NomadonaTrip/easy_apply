import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
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

  it('should display app name as link to dashboard', () => {
    render(<Header />, { wrapper: createWrapper() });

    const appName = screen.getByText('easy_apply');
    expect(appName).toBeInTheDocument();
    expect(appName.closest('a')).toHaveAttribute('href', '/dashboard');
  });

  it('should show hamburger menu when user is authenticated', () => {
    useAuthStore.setState({
      user: mockUser,
      isAuthenticated: true,
    });
    vi.mocked(rolesApi.getRoles).mockResolvedValue([]);

    render(<Header />, { wrapper: createWrapper() });

    expect(screen.getByRole('button', { name: /open menu/i })).toBeInTheDocument();
  });

  it('should not show hamburger menu when user is not authenticated', () => {
    useAuthStore.setState({
      user: null,
      isAuthenticated: false,
    });

    render(<Header />, { wrapper: createWrapper() });

    expect(screen.queryByRole('button', { name: /open menu/i })).not.toBeInTheDocument();
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
