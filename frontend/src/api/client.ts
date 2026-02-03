/**
 * API client for communicating with the backend.
 * Handles request/response serialization and error handling.
 */

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
 * @param endpoint The API endpoint path (e.g., '/auth/register')
 * @param options Fetch options (method, body, headers, etc.)
 * @returns The parsed JSON response
 * @throws ApiRequestError with the detail message from the API
 */
export async function apiRequest<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    credentials: 'include', // Always include cookies
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
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
