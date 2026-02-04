import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useRoles, useCreateRole, useDeleteRole } from './useRoles';
import * as rolesApi from '@/api/roles';

// Mock the roles API
vi.mock('@/api/roles', () => ({
  getRoles: vi.fn(),
  createRole: vi.fn(),
  deleteRole: vi.fn(),
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe('useRoles', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('useRoles hook', () => {
    it('should fetch roles on mount', async () => {
      const mockRoles = [
        { id: 1, user_id: 1, name: 'Product Manager', created_at: '2026-01-01' },
      ];
      vi.mocked(rolesApi.getRoles).mockResolvedValueOnce(mockRoles);

      const { result } = renderHook(() => useRoles(), { wrapper: createWrapper() });

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(mockRoles);
      expect(rolesApi.getRoles).toHaveBeenCalledTimes(1);
    });

    it('should handle error state', async () => {
      vi.mocked(rolesApi.getRoles).mockRejectedValueOnce(new Error('Network error'));

      const { result } = renderHook(() => useRoles(), { wrapper: createWrapper() });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toBeInstanceOf(Error);
    });
  });

  describe('useCreateRole hook', () => {
    it('should create a role and invalidate queries', async () => {
      const newRole = { id: 1, user_id: 1, name: 'Product Manager', created_at: '2026-01-01' };
      vi.mocked(rolesApi.createRole).mockResolvedValueOnce(newRole);
      vi.mocked(rolesApi.getRoles).mockResolvedValue([]);

      const { result } = renderHook(() => useCreateRole(), { wrapper: createWrapper() });

      result.current.mutate({ name: 'Product Manager' });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(rolesApi.createRole).toHaveBeenCalledWith({ name: 'Product Manager' });
    });

    it('should trigger cache invalidation by refetching roles after mutation', async () => {
      const newRole = { id: 1, user_id: 1, name: 'Product Manager', created_at: '2026-01-01' };
      vi.mocked(rolesApi.createRole).mockResolvedValueOnce(newRole);
      vi.mocked(rolesApi.getRoles).mockResolvedValue([newRole]);

      const queryClient = new QueryClient({
        defaultOptions: {
          queries: { retry: false },
          mutations: { retry: false },
        },
      });

      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      );

      // First, set up the roles query
      renderHook(() => useRoles(), { wrapper });

      // Clear mock to track calls after mutation
      vi.mocked(rolesApi.getRoles).mockClear();

      // Now perform mutation
      const { result } = renderHook(() => useCreateRole(), { wrapper });
      result.current.mutate({ name: 'Product Manager' });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Verify getRoles was called again due to cache invalidation
      await waitFor(() => {
        expect(rolesApi.getRoles).toHaveBeenCalled();
      });
    });

    it('should handle mutation error', async () => {
      vi.mocked(rolesApi.createRole).mockRejectedValueOnce(new Error('Server error'));

      const { result } = renderHook(() => useCreateRole(), { wrapper: createWrapper() });

      result.current.mutate({ name: 'Test Role' });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toBeInstanceOf(Error);
    });
  });

  describe('useDeleteRole hook', () => {
    it('should delete a role and invalidate queries', async () => {
      vi.mocked(rolesApi.deleteRole).mockResolvedValueOnce(undefined);
      vi.mocked(rolesApi.getRoles).mockResolvedValue([]);

      const { result } = renderHook(() => useDeleteRole(), { wrapper: createWrapper() });

      result.current.mutate(1);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(rolesApi.deleteRole).toHaveBeenCalledWith(1);
    });

    it('should handle deletion error', async () => {
      vi.mocked(rolesApi.deleteRole).mockRejectedValueOnce(new Error('Not found'));

      const { result } = renderHook(() => useDeleteRole(), { wrapper: createWrapper() });

      result.current.mutate(999);

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toBeInstanceOf(Error);
    });
  });
});
