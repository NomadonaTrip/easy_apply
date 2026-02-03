/**
 * Authentication API functions.
 * Handles user registration, login, and account limit checks.
 */

import { apiRequest } from './client';

export interface UserCreate {
  username: string;
  password: string;
}

export interface UserRead {
  id: number;
  username: string;
  created_at: string;
}

export interface AccountLimit {
  current_count: number;
  max_accounts: number;
  registration_allowed: boolean;
}

/**
 * Register a new user account.
 *
 * @param data User registration data (username and password)
 * @returns The created user (without password_hash)
 * @throws Error if registration fails
 */
export async function register(data: UserCreate): Promise<UserRead> {
  return apiRequest<UserRead>('/auth/register', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Check if new user registrations are allowed.
 *
 * @returns Account limit status
 */
export async function checkAccountLimit(): Promise<AccountLimit> {
  return apiRequest<AccountLimit>('/auth/account-limit');
}

export interface LoginRequest {
  username: string;
  password: string;
}

/**
 * Login with username and password.
 *
 * @param data Login credentials
 * @returns The authenticated user
 * @throws Error if login fails
 */
export async function login(data: LoginRequest): Promise<UserRead> {
  return apiRequest<UserRead>('/auth/login', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Logout the current user.
 *
 * @throws Error if logout fails
 */
export async function logout(): Promise<void> {
  await apiRequest('/auth/logout', {
    method: 'POST',
  });
}
