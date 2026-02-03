import { create } from 'zustand';
import { logout as logoutApi } from '@/api/auth';

export interface User {
  id: number;
  username: string;
  created_at: string;
}

interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  isLoggingOut: boolean;
  logoutError: string | null;
  setUser: (user: User | null) => void;
  checkAuth: () => Promise<void>;
  logout: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isLoading: true,
  isAuthenticated: false,
  isLoggingOut: false,
  logoutError: null,

  setUser: (user) => set({
    user,
    isAuthenticated: !!user,
    isLoading: false,
  }),

  checkAuth: async () => {
    try {
      const response = await fetch('/api/v1/auth/me', {
        credentials: 'include',
      });
      if (response.ok) {
        const user = await response.json();
        set({ user, isAuthenticated: true, isLoading: false });
      } else {
        set({ user: null, isAuthenticated: false, isLoading: false });
      }
    } catch {
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  },

  logout: async () => {
    set({ isLoggingOut: true, logoutError: null });
    try {
      await logoutApi();
      set({ user: null, isAuthenticated: false, isLoggingOut: false });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Logout failed';
      if (import.meta.env.DEV) {
        console.error('Logout error:', error);
      }
      set({ logoutError: message, isLoggingOut: false });
      // Still clear local state for security
      set({ user: null, isAuthenticated: false });
    }
  },
}));
