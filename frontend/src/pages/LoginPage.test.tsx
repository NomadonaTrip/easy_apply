import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { LoginPage } from './LoginPage'
import { useAuthStore } from '@/stores/authStore'
import * as authApi from '@/api/auth'

// Mock the auth API
vi.mock('@/api/auth', () => ({
  login: vi.fn(),
}))

// Mock react-router-dom's useNavigate
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

function renderLoginPage() {
  return render(
    <BrowserRouter>
      <LoginPage />
    </BrowserRouter>
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

    it('should render link to register page', () => {
      renderLoginPage()
      expect(screen.getByRole('link', { name: /register/i })).toBeInTheDocument()
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
        expect(mockNavigate).toHaveBeenCalledWith('/dashboard')
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

    it('should have aria-describedby linking error to inputs', async () => {
      vi.mocked(authApi.login).mockRejectedValueOnce(new Error('Error'))

      renderLoginPage()

      fireEvent.change(screen.getByLabelText(/username/i), {
        target: { value: 'test' },
      })
      fireEvent.change(screen.getByLabelText(/password/i), {
        target: { value: 'test' },
      })
      fireEvent.click(screen.getByRole('button', { name: /login/i }))

      await waitFor(() => {
        expect(screen.getByLabelText(/username/i)).toHaveAttribute(
          'aria-describedby',
          'login-error'
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

      expect(mockNavigate).toHaveBeenCalledWith('/dashboard')
    })
  })
})
