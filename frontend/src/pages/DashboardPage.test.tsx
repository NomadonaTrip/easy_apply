import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DashboardPage } from './DashboardPage';
import { useAuthStore } from '@/stores/authStore';

// Mock the auth store
vi.mock('@/stores/authStore');

const mockUseAuthStore = useAuthStore as unknown as ReturnType<typeof vi.fn>;

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('displays welcome message with username', () => {
    mockUseAuthStore.mockReturnValue({
      user: { id: 1, username: 'testuser', created_at: '2026-01-01' },
    });

    render(<DashboardPage />);

    expect(screen.getByText('Welcome, testuser!')).toBeInTheDocument();
  });

  it('displays welcome message without username when user is null', () => {
    mockUseAuthStore.mockReturnValue({
      user: null,
    });

    render(<DashboardPage />);

    expect(screen.getByText('Welcome!')).toBeInTheDocument();
  });

  it('renders dashboard content', () => {
    mockUseAuthStore.mockReturnValue({
      user: { id: 1, username: 'testuser', created_at: '2026-01-01' },
    });

    render(<DashboardPage />);

    expect(screen.getByText(/You have successfully logged in/i)).toBeInTheDocument();
    expect(screen.getByText(/Role management and application features/i)).toBeInTheDocument();
  });

});
