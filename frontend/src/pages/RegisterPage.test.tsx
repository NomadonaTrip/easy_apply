import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RegisterPage } from './RegisterPage';
import * as authApi from '@/api/auth';

// Mock the auth API
vi.mock('@/api/auth', () => ({
  register: vi.fn(),
  checkAccountLimit: vi.fn(),
}));

// Mock react-router-dom's useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

function renderRegisterPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <RegisterPage />
      </BrowserRouter>
    </QueryClientProvider>
  );
}

describe('RegisterPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default to registration allowed
    vi.mocked(authApi.checkAccountLimit).mockResolvedValue({
      current_count: 0,
      max_accounts: 2,
      registration_allowed: true,
    });
  });

  describe('loading state', () => {
    it('should show loading state while checking account limit', async () => {
      // Make the query hang
      vi.mocked(authApi.checkAccountLimit).mockImplementation(
        () => new Promise(() => {})
      );

      renderRegisterPage();

      expect(screen.getByText('Loading...')).toBeInTheDocument();
    });
  });

  describe('registration unavailable', () => {
    it('should show unavailable message when max accounts reached', async () => {
      vi.mocked(authApi.checkAccountLimit).mockResolvedValue({
        current_count: 2,
        max_accounts: 2,
        registration_allowed: false,
      });

      renderRegisterPage();

      await waitFor(() => {
        expect(screen.getByText('Registration Unavailable')).toBeInTheDocument();
      });
      expect(screen.getByText('Maximum accounts reached (2)')).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /go to login/i })).toBeInTheDocument();
    });
  });

  describe('service unavailable', () => {
    it('should show error state when API fails', async () => {
      vi.mocked(authApi.checkAccountLimit).mockRejectedValue(
        new Error('Network error')
      );

      renderRegisterPage();

      await waitFor(() => {
        expect(screen.getByText('Service Unavailable')).toBeInTheDocument();
      });
      expect(
        screen.getByText(/unable to connect to the server/i)
      ).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
    });
  });

  describe('rendering', () => {
    it('should render username input', async () => {
      renderRegisterPage();

      await waitFor(() => {
        expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
      });
    });

    it('should render password input', async () => {
      renderRegisterPage();

      await waitFor(() => {
        expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
      });
    });

    it('should render register button', async () => {
      renderRegisterPage();

      await waitFor(() => {
        expect(
          screen.getByRole('button', { name: /register/i })
        ).toBeInTheDocument();
      });
    });

    it('should render link to login page', async () => {
      renderRegisterPage();

      await waitFor(() => {
        expect(screen.getByRole('link', { name: /login/i })).toBeInTheDocument();
      });
    });
  });

  describe('form submission', () => {
    it('should call register API with form values', async () => {
      const mockUser = { id: 1, username: 'newuser', created_at: '2026-01-01' };
      vi.mocked(authApi.register).mockResolvedValueOnce(mockUser);

      renderRegisterPage();

      await waitFor(() => {
        expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
      });

      fireEvent.change(screen.getByLabelText(/username/i), {
        target: { value: 'newuser' },
      });
      fireEvent.change(screen.getByLabelText(/password/i), {
        target: { value: 'password123' },
      });
      fireEvent.click(screen.getByRole('button', { name: /register/i }));

      await waitFor(() => {
        expect(authApi.register).toHaveBeenCalledWith({
          username: 'newuser',
          password: 'password123',
        });
      });
    });

    it('should disable button while loading', async () => {
      vi.mocked(authApi.register).mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 100))
      );

      renderRegisterPage();

      await waitFor(() => {
        expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
      });

      fireEvent.change(screen.getByLabelText(/username/i), {
        target: { value: 'newuser' },
      });
      fireEvent.change(screen.getByLabelText(/password/i), {
        target: { value: 'password123' },
      });
      fireEvent.click(screen.getByRole('button', { name: /register/i }));

      expect(screen.getByRole('button')).toBeDisabled();
      expect(screen.getByRole('button')).toHaveTextContent(/creating account/i);
    });

    it('should navigate to login on success', async () => {
      const mockUser = { id: 1, username: 'newuser', created_at: '2026-01-01' };
      vi.mocked(authApi.register).mockResolvedValueOnce(mockUser);

      renderRegisterPage();

      await waitFor(() => {
        expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
      });

      fireEvent.change(screen.getByLabelText(/username/i), {
        target: { value: 'newuser' },
      });
      fireEvent.change(screen.getByLabelText(/password/i), {
        target: { value: 'password123' },
      });
      fireEvent.click(screen.getByRole('button', { name: /register/i }));

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/login');
      });
    });
  });

  describe('error handling', () => {
    it('should display error message on failed registration', async () => {
      vi.mocked(authApi.register).mockRejectedValueOnce(
        new Error('Username already taken')
      );

      renderRegisterPage();

      await waitFor(() => {
        expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
      });

      fireEvent.change(screen.getByLabelText(/username/i), {
        target: { value: 'taken' },
      });
      fireEvent.change(screen.getByLabelText(/password/i), {
        target: { value: 'password123' },
      });
      fireEvent.click(screen.getByRole('button', { name: /register/i }));

      await waitFor(() => {
        expect(screen.getByRole('alert')).toHaveTextContent(
          'Username already taken'
        );
      });
    });
  });

  describe('client-side validation', () => {
    it('should show error for username too short', async () => {
      renderRegisterPage();

      await waitFor(() => {
        expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
      });

      fireEvent.change(screen.getByLabelText(/username/i), {
        target: { value: 'ab' },
      });
      fireEvent.change(screen.getByLabelText(/password/i), {
        target: { value: 'password123' },
      });
      fireEvent.click(screen.getByRole('button', { name: /register/i }));

      await waitFor(() => {
        expect(screen.getByRole('alert')).toHaveTextContent(
          'Username must be 3-50 characters'
        );
      });
      expect(authApi.register).not.toHaveBeenCalled();
    });

    it('should show error for password too short', async () => {
      renderRegisterPage();

      await waitFor(() => {
        expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
      });

      fireEvent.change(screen.getByLabelText(/username/i), {
        target: { value: 'validuser' },
      });
      fireEvent.change(screen.getByLabelText(/password/i), {
        target: { value: 'short' },
      });
      fireEvent.click(screen.getByRole('button', { name: /register/i }));

      await waitFor(() => {
        expect(screen.getByRole('alert')).toHaveTextContent(
          'Password must be at least 8 characters'
        );
      });
      expect(authApi.register).not.toHaveBeenCalled();
    });
  });
});
