import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useRoleStore, Role } from './roleStore';

// Mock queryClient
vi.mock('@/lib/queryClient', () => ({
  queryClient: {
    invalidateQueries: vi.fn(),
    clear: vi.fn(),
  },
}));

describe('roleStore', () => {
  const mockRole: Role = {
    id: 1,
    user_id: 1,
    name: 'Software Engineer',
    created_at: '2026-02-03T00:00:00Z',
  };

  const mockRole2: Role = {
    id: 2,
    user_id: 1,
    name: 'Product Manager',
    created_at: '2026-02-03T00:00:00Z',
  };

  beforeEach(() => {
    // Reset store state before each test
    useRoleStore.setState({ currentRole: null });
    // Clear localStorage
    localStorage.clear();
    vi.clearAllMocks();
  });

  describe('initial state', () => {
    it('should have null currentRole initially', () => {
      const state = useRoleStore.getState();
      expect(state.currentRole).toBeNull();
    });
  });

  describe('setCurrentRole', () => {
    it('should set the current role', () => {
      const { setCurrentRole } = useRoleStore.getState();

      setCurrentRole(mockRole);

      const state = useRoleStore.getState();
      expect(state.currentRole).toEqual(mockRole);
    });

    it('should update when switching to a different role', () => {
      const { setCurrentRole } = useRoleStore.getState();

      setCurrentRole(mockRole);
      setCurrentRole(mockRole2);

      const state = useRoleStore.getState();
      expect(state.currentRole).toEqual(mockRole2);
    });

    it('should invalidate role-scoped queries on role change', async () => {
      const { queryClient } = await import('@/lib/queryClient');
      const { setCurrentRole } = useRoleStore.getState();

      setCurrentRole(mockRole);

      expect(queryClient.invalidateQueries).toHaveBeenCalledWith({
        queryKey: ['applications'],
      });
      expect(queryClient.invalidateQueries).toHaveBeenCalledWith({
        queryKey: ['skills'],
      });
      expect(queryClient.invalidateQueries).toHaveBeenCalledWith({
        queryKey: ['accomplishments'],
      });
      expect(queryClient.invalidateQueries).toHaveBeenCalledWith({
        queryKey: ['experience'],
      });
      expect(queryClient.invalidateQueries).toHaveBeenCalledWith({
        queryKey: ['resumes'],
      });
    });
  });

  describe('clearCurrentRole', () => {
    it('should clear the current role', () => {
      const { setCurrentRole, clearCurrentRole } = useRoleStore.getState();

      setCurrentRole(mockRole);
      clearCurrentRole();

      const state = useRoleStore.getState();
      expect(state.currentRole).toBeNull();
    });

    it('should clear all cached data on role clear', async () => {
      const { queryClient } = await import('@/lib/queryClient');
      const { setCurrentRole, clearCurrentRole } = useRoleStore.getState();

      setCurrentRole(mockRole);
      vi.clearAllMocks();
      clearCurrentRole();

      expect(queryClient.clear).toHaveBeenCalled();
    });
  });

  describe('persistence', () => {
    it('should persist currentRole to localStorage', () => {
      const { setCurrentRole } = useRoleStore.getState();

      setCurrentRole(mockRole);

      const stored = localStorage.getItem('role-storage');
      expect(stored).not.toBeNull();

      const parsed = JSON.parse(stored!);
      expect(parsed.state.currentRole).toEqual(mockRole);
    });

    it('should use the correct storage key for persistence', () => {
      const { setCurrentRole } = useRoleStore.getState();

      setCurrentRole(mockRole);

      // Verify the storage key is 'role-storage' as specified
      expect(localStorage.getItem('role-storage')).not.toBeNull();
      expect(localStorage.getItem('some-other-key')).toBeNull();
    });

    it('should only persist currentRole (partialize)', () => {
      const { setCurrentRole } = useRoleStore.getState();

      setCurrentRole(mockRole);

      const stored = localStorage.getItem('role-storage');
      const parsed = JSON.parse(stored!);

      // Verify only currentRole is persisted (not functions)
      expect(parsed.state).toHaveProperty('currentRole');
      expect(parsed.state).not.toHaveProperty('setCurrentRole');
      expect(parsed.state).not.toHaveProperty('clearCurrentRole');
    });
  });
});
