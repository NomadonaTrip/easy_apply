/**
 * API client for role management operations.
 */

import { apiRequest } from './client';

export interface Role {
  id: number;
  user_id: number;
  name: string;
  created_at: string;
}

export interface RoleCreate {
  name: string;
}

/**
 * Fetch all roles for the current user.
 */
export async function getRoles(): Promise<Role[]> {
  return apiRequest<Role[]>('/roles');
}

/**
 * Create a new role.
 */
export async function createRole(data: RoleCreate): Promise<Role> {
  return apiRequest<Role>('/roles', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Delete a role by ID.
 */
export async function deleteRole(roleId: number): Promise<void> {
  return apiRequest<void>(`/roles/${roleId}`, {
    method: 'DELETE',
  });
}
