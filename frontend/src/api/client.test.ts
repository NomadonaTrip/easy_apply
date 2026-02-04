import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { apiRequest, ApiRequestError } from './client';
import { useRoleStore } from '@/stores/roleStore';

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('apiRequest', () => {
  const mockRole = {
    id: 42,
    user_id: 1,
    name: 'Software Engineer',
    created_at: '2026-02-03T00:00:00Z',
  };

  beforeEach(() => {
    mockFetch.mockReset();
    useRoleStore.setState({ currentRole: null });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('X-Role-Id header injection', () => {
    it('should add X-Role-Id header when role is selected for non-auth endpoints', async () => {
      useRoleStore.setState({ currentRole: mockRole });
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ data: 'test' }),
      });

      await apiRequest('/applications');

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/applications',
        expect.objectContaining({
          headers: expect.objectContaining({
            'X-Role-Id': '42',
          }),
        })
      );
    });

    it('should NOT add X-Role-Id header for auth endpoints', async () => {
      useRoleStore.setState({ currentRole: mockRole });
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ user: 'test' }),
      });

      await apiRequest('/auth/me');

      const callArgs = mockFetch.mock.calls[0][1];
      expect(callArgs.headers['X-Role-Id']).toBeUndefined();
    });

    it('should NOT add X-Role-Id header for /auth/login', async () => {
      useRoleStore.setState({ currentRole: mockRole });
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ user: 'test' }),
      });

      await apiRequest('/auth/login', { method: 'POST', body: '{}' });

      const callArgs = mockFetch.mock.calls[0][1];
      expect(callArgs.headers['X-Role-Id']).toBeUndefined();
    });

    it('should NOT add X-Role-Id header for /roles endpoint', async () => {
      useRoleStore.setState({ currentRole: mockRole });
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve([]),
      });

      await apiRequest('/roles');

      const callArgs = mockFetch.mock.calls[0][1];
      expect(callArgs.headers['X-Role-Id']).toBeUndefined();
    });

    it('should NOT add X-Role-Id header for /roles/:id endpoint', async () => {
      useRoleStore.setState({ currentRole: mockRole });
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 204,
      });

      await apiRequest('/roles/1', { method: 'DELETE' });

      const callArgs = mockFetch.mock.calls[0][1];
      expect(callArgs.headers['X-Role-Id']).toBeUndefined();
    });

    it('should throw error when no role selected for role-scoped endpoints', async () => {
      useRoleStore.setState({ currentRole: null });

      await expect(apiRequest('/applications')).rejects.toThrow(
        'No role selected. Please select a role first.'
      );

      expect(mockFetch).not.toHaveBeenCalled();
    });

    it('should allow auth endpoints without role selected', async () => {
      useRoleStore.setState({ currentRole: null });
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ user: 'test' }),
      });

      await expect(apiRequest('/auth/me')).resolves.toEqual({ user: 'test' });
    });

    it('should allow /roles endpoint without role selected', async () => {
      useRoleStore.setState({ currentRole: null });
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve([]),
      });

      await expect(apiRequest('/roles')).resolves.toEqual([]);
    });

    it('should require X-Role-Id header for endpoints that look like but are not /roles', async () => {
      useRoleStore.setState({ currentRole: null });

      await expect(apiRequest('/roles-extended')).rejects.toThrow(
        'No role selected. Please select a role first.'
      );

      expect(mockFetch).not.toHaveBeenCalled();
    });
  });

  describe('error handling', () => {
    it('should throw ApiRequestError on non-ok response', async () => {
      useRoleStore.setState({ currentRole: mockRole });
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: () => Promise.resolve({ detail: 'Not found' }),
      });

      await expect(apiRequest('/applications/999')).rejects.toThrow(ApiRequestError);
    });

    it('should handle 204 No Content response', async () => {
      useRoleStore.setState({ currentRole: mockRole });
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 204,
      });

      const result = await apiRequest('/applications/1', { method: 'DELETE' });
      expect(result).toBeUndefined();
    });
  });
});
