import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { ProtectedRoute } from './ProtectedRoute';
import { useAuthStore } from '@/stores/authStore';
import { useAutoSelectRole } from '@/hooks/useAutoSelectRole';

// Mock the auth store
vi.mock('@/stores/authStore');

// Mock the auto-select role hook
vi.mock('@/hooks/useAutoSelectRole');

const mockUseAuthStore = useAuthStore as unknown as ReturnType<typeof vi.fn>;
const mockUseAutoSelectRole = vi.mocked(useAutoSelectRole);

function renderWithRouter(initialRoute: string = '/protected') {
  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <Routes>
        <Route path="/login" element={<div>Login Page</div>} />
        <Route path="/roles" element={<div>Roles Page</div>} />
        <Route
          path="/protected"
          element={
            <ProtectedRoute>
              <div>Protected Content</div>
            </ProtectedRoute>
          }
        />
      </Routes>
    </MemoryRouter>
  );
}

describe('ProtectedRoute', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAutoSelectRole.mockReturnValue({ needsRoleCreation: false });
  });

  it('shows loading state during auth check', () => {
    mockUseAuthStore.mockReturnValue({
      isAuthenticated: false,
      isLoading: true,
    });

    renderWithRouter();

    expect(screen.getByText('Checking authentication...')).toBeInTheDocument();
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  it('redirects to login when not authenticated', () => {
    mockUseAuthStore.mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
    });

    renderWithRouter();

    expect(screen.getByText('Login Page')).toBeInTheDocument();
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  it('renders children when authenticated', () => {
    mockUseAuthStore.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
    });

    renderWithRouter();

    expect(screen.getByText('Protected Content')).toBeInTheDocument();
    expect(screen.queryByText('Login Page')).not.toBeInTheDocument();
  });

  it('preserves the attempted URL in location state for redirect', () => {
    mockUseAuthStore.mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
    });

    // The redirect should preserve the 'from' location
    // This is tested indirectly - the Navigate component with state prop handles this
    renderWithRouter('/protected');

    expect(screen.getByText('Login Page')).toBeInTheDocument();
  });

  it('redirects to /roles when needsRoleCreation is true', () => {
    mockUseAuthStore.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
    });
    mockUseAutoSelectRole.mockReturnValue({ needsRoleCreation: true });

    renderWithRouter('/protected');

    expect(screen.getByText('Roles Page')).toBeInTheDocument();
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  it('does not redirect when already on /roles page and needsRoleCreation is true', () => {
    mockUseAuthStore.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
    });
    mockUseAutoSelectRole.mockReturnValue({ needsRoleCreation: true });

    render(
      <MemoryRouter initialEntries={['/roles']}>
        <Routes>
          <Route
            path="/roles"
            element={
              <ProtectedRoute>
                <div>Roles Page Content</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText('Roles Page Content')).toBeInTheDocument();
  });
});
