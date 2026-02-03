/**
 * API client for communicating with the backend.
 * Handles request/response serialization and error handling.
 */

const API_BASE = '/api/v1';

export interface ApiError {
  detail: string | string[];
}

/**
 * Make an API request to the backend.
 *
 * @param endpoint The API endpoint path (e.g., '/auth/register')
 * @param options Fetch options (method, body, headers, etc.)
 * @returns The parsed JSON response
 * @throws Error with the detail message from the API
 */
export async function apiRequest<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error: ApiError = await response.json();
    const detail = Array.isArray(error.detail)
      ? error.detail[0]?.msg || 'An error occurred'
      : error.detail;
    throw new Error(detail);
  }

  return response.json();
}
