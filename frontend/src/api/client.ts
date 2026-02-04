/**
 * API client for communicating with the backend.
 * Handles request/response serialization, error handling, and X-Role-Id header injection.
 */

import { useRoleStore } from '@/stores/roleStore';

const API_BASE = '/api/v1';

export interface ApiError {
  detail: string | { msg: string; type: string; loc: string[] }[];
}

export class ApiRequestError extends Error {
  constructor(
    message: string,
    public status: number,
    public detail: ApiError['detail']
  ) {
    super(message);
    this.name = 'ApiRequestError';
  }
}

/**
 * Make an API request to the backend.
 *
 * Automatically injects X-Role-Id header for role-scoped endpoints.
 * Auth endpoints (/auth/*) and role management (/roles) don't require X-Role-Id.
 *
 * @param endpoint The API endpoint path (e.g., '/auth/register')
 * @param options Fetch options (method, body, headers, etc.)
 * @returns The parsed JSON response
 * @throws ApiRequestError with the detail message from the API
 * @throws Error if no role is selected for role-scoped endpoints
 */
export async function apiRequest<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const { currentRole } = useRoleStore.getState();

  // These endpoints don't require role context
  const isAuthEndpoint = endpoint.startsWith('/auth/');
  const isRolesEndpoint = /^\/roles(\/\d+)?(\?.*)?$/.test(endpoint);

  // Require role selection for role-scoped endpoints
  if (!currentRole && !isAuthEndpoint && !isRolesEndpoint) {
    throw new Error('No role selected. Please select a role first.');
  }

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers as Record<string, string>),
  };

  // Add X-Role-Id header for role-scoped requests
  if (currentRole && !isAuthEndpoint && !isRolesEndpoint) {
    headers['X-Role-Id'] = currentRole.id.toString();
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    credentials: 'include', // Always include cookies
    headers,
  });

  if (!response.ok) {
    const error: ApiError = await response.json().catch(() => ({
      detail: 'An unexpected error occurred',
    }));

    const message =
      typeof error.detail === 'string'
        ? error.detail
        : error.detail[0]?.msg || 'Request failed';

    throw new ApiRequestError(message, response.status, error.detail);
  }

  // Handle empty responses (204 No Content)
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}
