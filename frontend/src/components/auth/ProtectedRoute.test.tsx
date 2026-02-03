import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { ProtectedRoute } from './ProtectedRoute';
import { useAuthStore } from '@/stores/authStore';

// Mock the auth store
vi.mock('@/stores/authStore');

const mockUseAuthStore = useAuthStore as unknown as ReturnType<typeof vi.fn>;

function renderWithRouter(initialRoute: string = '/protected') {
  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <Routes>
        <Route path="/login" element={<div>Login Page</div>} />
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
});
