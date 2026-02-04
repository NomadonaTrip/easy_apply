import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getRoles, createRole, deleteRole, type Role, type RoleCreate } from '@/api/roles';

/**
 * Hook to fetch all roles for the current user.
 */
export function useRoles() {
  return useQuery({
    queryKey: ['roles'],
    queryFn: getRoles,
  });
}

/**
 * Hook to create a new role.
 * Automatically invalidates the roles query on success.
 */
export function useCreateRole() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: RoleCreate) => createRole(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['roles'] });
    },
  });
}

/**
 * Hook to delete a role.
 * Automatically invalidates the roles query on success.
 */
export function useDeleteRole() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (roleId: number) => deleteRole(roleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['roles'] });
    },
  });
}

// Re-export types for convenience
export type { Role, RoleCreate };
