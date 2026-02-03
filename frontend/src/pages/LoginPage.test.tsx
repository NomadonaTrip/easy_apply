import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { LoginPage } from './LoginPage'
import { useAuthStore } from '@/stores/authStore'
import * as authApi from '@/api/auth'

// Mock the auth API
vi.mock('@/api/auth', () => ({
  login: vi.fn(),
  checkAccountLimit: vi.fn(),
}))

// Mock react-router-dom's useNavigate and useLocation
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useLocation: () => ({ state: null }),
  }
})

function renderLoginPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <LoginPage />
      </BrowserRouter>
    </QueryClientProvider>
  )
}

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Reset auth store
    useAuthStore.setState({
      user: null,
      isLoading: false,
      isAuthenticated: false,
    })
    // Default to registration allowed
    vi.mocked(authApi.checkAccountLimit).mockResolvedValue({
      current_count: 0,
      max_accounts: 2,
      registration_allowed: true,
    })
  })

  describe('rendering', () => {
    it('should render username input', () => {
      renderLoginPage()
      expect(screen.getByLabelText(/username/i)).toBeInTheDocument()
    })

    it('should render password input', () => {
      renderLoginPage()
      expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
    })

    it('should render login button', () => {
      renderLoginPage()
      expect(screen.getByRole('button', { name: /login/i })).toBeInTheDocument()
    })

    it('should render link to register page when registration allowed', async () => {
      vi.mocked(authApi.checkAccountLimit).mockResolvedValue({
        current_count: 0,
        max_accounts: 2,
        registration_allowed: true,
      })

      renderLoginPage()

      await waitFor(() => {
        expect(screen.getByRole('link', { name: /register/i })).toBeInTheDocument()
      })
    })

    it('should hide register link when max accounts reached', async () => {
      vi.mocked(authApi.checkAccountLimit).mockResolvedValue({
        current_count: 2,
        max_accounts: 2,
        registration_allowed: false,
      })

      renderLoginPage()

      // Wait for the query to complete, then verify no register link
      await waitFor(() => {
        expect(screen.queryByRole('link', { name: /register/i })).not.toBeInTheDocument()
      })
    })
  })

  describe('form submission', () => {
    it('should call login API with form values', async () => {
      const mockUser = { id: 1, username: 'testuser', created_at: '2026-01-01' }
      vi.mocked(authApi.login).mockResolvedValueOnce(mockUser)

      renderLoginPage()

      fireEvent.change(screen.getByLabelText(/username/i), {
        target: { value: 'testuser' },
      })
      fireEvent.change(screen.getByLabelText(/password/i), {
        target: { value: 'password123' },
      })
      fireEvent.click(screen.getByRole('button', { name: /login/i }))

      await waitFor(() => {
        expect(authApi.login).toHaveBeenCalledWith({
          username: 'testuser',
          password: 'password123',
        })
      })
    })

    it('should disable button while loading', async () => {
      vi.mocked(authApi.login).mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 100))
      )

      renderLoginPage()

      fireEvent.change(screen.getByLabelText(/username/i), {
        target: { value: 'testuser' },
      })
      fireEvent.change(screen.getByLabelText(/password/i), {
        target: { value: 'password123' },
      })
      fireEvent.click(screen.getByRole('button', { name: /login/i }))

      expect(screen.getByRole('button')).toBeDisabled()
      expect(screen.getByRole('button')).toHaveTextContent(/signing in/i)
    })

    it('should navigate to dashboard on success', async () => {
      const mockUser = { id: 1, username: 'testuser', created_at: '2026-01-01' }
      vi.mocked(authApi.login).mockResolvedValueOnce(mockUser)

      renderLoginPage()

      fireEvent.change(screen.getByLabelText(/username/i), {
        target: { value: 'testuser' },
      })
      fireEvent.change(screen.getByLabelText(/password/i), {
        target: { value: 'password123' },
      })
      fireEvent.click(screen.getByRole('button', { name: /login/i }))

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/dashboard', { replace: true })
      })
    })
  })

  describe('error handling', () => {
    it('should display error message on failed login', async () => {
      vi.mocked(authApi.login).mockRejectedValueOnce(
        new Error('Invalid username or password')
      )

      renderLoginPage()

      fireEvent.change(screen.getByLabelText(/username/i), {
        target: { value: 'wrong' },
      })
      fireEvent.change(screen.getByLabelText(/password/i), {
        target: { value: 'wrong' },
      })
      fireEvent.click(screen.getByRole('button', { name: /login/i }))

      await waitFor(() => {
        expect(screen.getByRole('alert')).toHaveTextContent(
          'Invalid username or password'
        )
      })
    })
  })

  describe('redirect when authenticated', () => {
    it('should redirect to dashboard when already authenticated', () => {
      useAuthStore.setState({
        user: { id: 1, username: 'test', created_at: '' },
        isAuthenticated: true,
        isLoading: false,
      })

      renderLoginPage()

      expect(mockNavigate).toHaveBeenCalledWith('/dashboard', { replace: true })
    })
  })
})
