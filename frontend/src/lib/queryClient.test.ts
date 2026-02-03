import { describe, it, expect } from 'vitest';
import { queryClient } from './queryClient';

describe('queryClient', () => {
  it('is configured with correct query defaults', () => {
    const defaultOptions = queryClient.getDefaultOptions();

    expect(defaultOptions.queries?.retry).toBe(1);
    expect(defaultOptions.queries?.staleTime).toBe(30 * 1000);
    expect(defaultOptions.queries?.gcTime).toBe(5 * 60 * 1000);
    expect(defaultOptions.queries?.refetchOnWindowFocus).toBe(false);
  });

  it('is configured with correct mutation defaults', () => {
    const defaultOptions = queryClient.getDefaultOptions();

    // Auth mutations should not retry to fail fast
    expect(defaultOptions.mutations?.retry).toBe(false);
  });
});
