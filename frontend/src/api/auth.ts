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
