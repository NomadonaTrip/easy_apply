import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useAuthStore } from './authStore'

describe('authStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    useAuthStore.setState({
      user: null,
      isLoading: true,
      isAuthenticated: false,
    })
  })

  describe('initial state', () => {
    it('should have null user', () => {
      const { user } = useAuthStore.getState()
      expect(user).toBeNull()
    })

    it('should have isLoading true', () => {
      const { isLoading } = useAuthStore.getState()
      expect(isLoading).toBe(true)
    })

    it('should have isAuthenticated false', () => {
      const { isAuthenticated } = useAuthStore.getState()
      expect(isAuthenticated).toBe(false)
    })
  })

  describe('setUser', () => {
    it('should set user and update isAuthenticated to true', () => {
      const mockUser = { id: 1, username: 'testuser', created_at: '2026-01-01' }

      useAuthStore.getState().setUser(mockUser)

      const state = useAuthStore.getState()
      expect(state.user).toEqual(mockUser)
      expect(state.isAuthenticated).toBe(true)
      expect(state.isLoading).toBe(false)
    })

    it('should set user to null and update isAuthenticated to false', () => {
      // First set a user
      useAuthStore.getState().setUser({ id: 1, username: 'test', created_at: '' })

      // Then set to null
      useAuthStore.getState().setUser(null)

      const state = useAuthStore.getState()
      expect(state.user).toBeNull()
      expect(state.isAuthenticated).toBe(false)
      expect(state.isLoading).toBe(false)
    })
  })

  describe('checkAuth', () => {
    it('should set user when /me returns successfully', async () => {
      const mockUser = { id: 1, username: 'authuser', created_at: '2026-01-01' }

      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockUser,
      } as Response)

      await useAuthStore.getState().checkAuth()

      const state = useAuthStore.getState()
      expect(state.user).toEqual(mockUser)
      expect(state.isAuthenticated).toBe(true)
      expect(state.isLoading).toBe(false)
    })

    it('should clear user when /me returns error', async () => {
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: false,
        status: 401,
      } as Response)

      await useAuthStore.getState().checkAuth()

      const state = useAuthStore.getState()
      expect(state.user).toBeNull()
      expect(state.isAuthenticated).toBe(false)
      expect(state.isLoading).toBe(false)
    })

    it('should clear user when fetch throws', async () => {
      vi.mocked(global.fetch).mockRejectedValueOnce(new Error('Network error'))

      await useAuthStore.getState().checkAuth()

      const state = useAuthStore.getState()
      expect(state.user).toBeNull()
      expect(state.isAuthenticated).toBe(false)
      expect(state.isLoading).toBe(false)
    })

    it('should call /api/v1/auth/me with credentials', async () => {
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: false,
      } as Response)

      await useAuthStore.getState().checkAuth()

      expect(global.fetch).toHaveBeenCalledWith('/api/v1/auth/me', {
        credentials: 'include',
      })
    })
  })

  describe('logout', () => {
    it('should clear user and set isAuthenticated to false', async () => {
      // Mock successful logout response
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        status: 204,
        json: async () => undefined,
      } as Response)

      // First set a user
      useAuthStore.getState().setUser({ id: 1, username: 'test', created_at: '' })

      // Then logout
      await useAuthStore.getState().logout()

      const state = useAuthStore.getState()
      expect(state.user).toBeNull()
      expect(state.isAuthenticated).toBe(false)
    })
  })
})
