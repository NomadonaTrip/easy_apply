import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useAutoSelectRole } from './useAutoSelectRole';
import { useRoleStore } from '@/stores/roleStore';
import * as rolesApi from '@/api/roles';

// Mock the roles API
vi.mock('@/api/roles', () => ({
  getRoles: vi.fn(),
  createRole: vi.fn(),
  deleteRole: vi.fn(),
}));

// Mock queryClient for roleStore
vi.mock('@/lib/queryClient', () => ({
  queryClient: {
    invalidateQueries: vi.fn(),
    clear: vi.fn(),
  },
}));

const mockRoles = [
  { id: 1, user_id: 1, name: 'Software Engineer', created_at: '2026-02-03T00:00:00Z' },
  { id: 2, user_id: 1, name: 'Product Manager', created_at: '2026-02-03T00:00:00Z' },
  { id: 3, user_id: 1, name: 'Data Scientist', created_at: '2026-02-03T00:00:00Z' },
];

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

describe('useAutoSelectRole', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useRoleStore.setState({ currentRole: null });
    localStorage.clear();
  });

  it('should auto-select first role when user has roles and no current role', async () => {
    vi.mocked(rolesApi.getRoles).mockResolvedValue(mockRoles);

    renderHook(() => useAutoSelectRole(), { wrapper: createWrapper() });

    await waitFor(() => {
      const state = useRoleStore.getState();
      expect(state.currentRole).toEqual(mockRoles[0]);
    });
  });

  it('should not change role if current role already exists in roles list', async () => {
    vi.mocked(rolesApi.getRoles).mockResolvedValue(mockRoles);
    useRoleStore.setState({ currentRole: mockRoles[1] }); // Product Manager

    renderHook(() => useAutoSelectRole(), { wrapper: createWrapper() });

    await waitFor(() => {
      const state = useRoleStore.getState();
      // Should still be Product Manager, not changed to first role
      expect(state.currentRole?.id).toBe(2);
    });
  });

  it('should reset to first role if current role no longer exists', async () => {
    vi.mocked(rolesApi.getRoles).mockResolvedValue(mockRoles);
    // Set a role that doesn't exist in the list
    useRoleStore.setState({
      currentRole: { id: 999, user_id: 1, name: 'Deleted Role', created_at: '2026-02-03' },
    });

    renderHook(() => useAutoSelectRole(), { wrapper: createWrapper() });

    await waitFor(
      () => {
        const state = useRoleStore.getState();
        // Should reset to first available role
        expect(state.currentRole?.id).toBe(1);
      },
      { timeout: 2000 }
    );
  });

  it('should not auto-select when user has no roles', async () => {
    vi.mocked(rolesApi.getRoles).mockResolvedValue([]);

    renderHook(() => useAutoSelectRole(), { wrapper: createWrapper() });

    // Wait for query to resolve
    await waitFor(() => {
      expect(rolesApi.getRoles).toHaveBeenCalled();
    });

    // Should remain null
    const state = useRoleStore.getState();
    expect(state.currentRole).toBeNull();
  });

  it('should return needsRoleCreation true when no roles exist', async () => {
    vi.mocked(rolesApi.getRoles).mockResolvedValue([]);

    const { result } = renderHook(() => useAutoSelectRole(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.needsRoleCreation).toBe(true);
    });
  });

  it('should return needsRoleCreation false when roles exist', async () => {
    vi.mocked(rolesApi.getRoles).mockResolvedValue(mockRoles);

    const { result } = renderHook(() => useAutoSelectRole(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.needsRoleCreation).toBe(false);
    });
  });
});
