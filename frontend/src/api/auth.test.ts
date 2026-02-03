import { describe, it, expect, vi, beforeEach } from 'vitest'
import { login, register, checkAccountLimit } from './auth'

describe('auth API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('login', () => {
    it('should call POST /api/v1/auth/login with credentials', async () => {
      const mockUser = { id: 1, username: 'testuser', created_at: '2026-01-01' }

      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockUser,
      } as Response)

      await login({ username: 'testuser', password: 'password123' })

      expect(global.fetch).toHaveBeenCalledWith('/api/v1/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username: 'testuser', password: 'password123' }),
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
      })
    })

    it('should return user on success', async () => {
      const mockUser = { id: 1, username: 'testuser', created_at: '2026-01-01' }

      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockUser,
      } as Response)

      const result = await login({ username: 'testuser', password: 'password123' })

      expect(result).toEqual(mockUser)
    })

    it('should throw error on 401', async () => {
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: 'Invalid username or password' }),
      } as Response)

      await expect(
        login({ username: 'wrong', password: 'wrong' })
      ).rejects.toThrow('Invalid username or password')
    })
  })

  describe('register', () => {
    it('should call POST /api/v1/auth/register', async () => {
      const mockUser = { id: 1, username: 'newuser', created_at: '2026-01-01' }

      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockUser,
      } as Response)

      await register({ username: 'newuser', password: 'password123' })

      expect(global.fetch).toHaveBeenCalledWith('/api/v1/auth/register', {
        method: 'POST',
        body: JSON.stringify({ username: 'newuser', password: 'password123' }),
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
      })
    })

    it('should return created user on success', async () => {
      const mockUser = { id: 1, username: 'newuser', created_at: '2026-01-01' }

      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockUser,
      } as Response)

      const result = await register({ username: 'newuser', password: 'password123' })

      expect(result).toEqual(mockUser)
    })

    it('should throw error when username taken', async () => {
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: 'Username already taken' }),
      } as Response)

      await expect(
        register({ username: 'taken', password: 'password123' })
      ).rejects.toThrow('Username already taken')
    })
  })

  describe('checkAccountLimit', () => {
    it('should return account limit info', async () => {
      const mockLimit = { current_count: 1, max_accounts: 2, registration_allowed: true }

      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockLimit,
      } as Response)

      const result = await checkAccountLimit()

      expect(result).toEqual(mockLimit)
      expect(global.fetch).toHaveBeenCalledWith('/api/v1/auth/account-limit', {
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
      })
    })
  })
})
