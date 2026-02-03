import { QueryClient } from '@tanstack/react-query';
import { ApiRequestError } from '@/api/client';
import { useAuthStore } from '@/stores/authStore';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Retry failed requests once
      retry: 1,
      // Consider data stale after 30 seconds
      staleTime: 30 * 1000,
      // Keep unused data in cache for 5 minutes
      gcTime: 5 * 60 * 1000,
      // Don't refetch on window focus for this app
      refetchOnWindowFocus: false,
    },
    mutations: {
      // Don't retry auth mutations - they should fail fast
      retry: false,
    },
  },
});

// Global handler for 401 responses - clears auth state on session expiry
queryClient.getQueryCache().config.onError = (error) => {
  if (error instanceof ApiRequestError && error.status === 401) {
    useAuthStore.getState().setUser(null);
  }
};

queryClient.getMutationCache().config.onError = (error) => {
  if (error instanceof ApiRequestError && error.status === 401) {
    useAuthStore.getState().setUser(null);
  }
};
