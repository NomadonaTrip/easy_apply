import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useResumes, useUploadResume, useDeleteResume } from './useResumes';

// Mock the API functions
vi.mock('@/api/resumes', () => ({
  getResumes: vi.fn(),
  uploadResume: vi.fn(),
  deleteResume: vi.fn(),
}));

// Mock the role store
vi.mock('@/stores/roleStore', () => ({
  useRoleStore: vi.fn((selector) =>
    selector({
      currentRole: { id: 1, user_id: 1, name: 'Test Role', created_at: '2026-01-01' },
    })
  ),
}));

import { getResumes, uploadResume, deleteResume } from '@/api/resumes';

describe('useResumes hooks', () => {
  let queryClient: QueryClient;

  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });
    vi.clearAllMocks();
  });

  describe('useResumes', () => {
    it('should fetch resumes when role is selected', async () => {
      const mockResumes = [
        {
          id: 1,
          role_id: 1,
          filename: 'resume.pdf',
          file_type: 'pdf',
          file_size: 1024,
          file_path: 'uploads/1/abc.pdf',
          uploaded_at: '2026-01-01T00:00:00Z',
          processed: false,
        },
      ];

      vi.mocked(getResumes).mockResolvedValueOnce(mockResumes);

      const { result } = renderHook(() => useResumes(), { wrapper });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toEqual(mockResumes);
      expect(getResumes).toHaveBeenCalled();
    });
  });

  describe('useUploadResume', () => {
    it('should upload a resume and invalidate queries', async () => {
      const mockResume = {
        id: 2,
        role_id: 1,
        filename: 'new.pdf',
        file_type: 'pdf',
        file_size: 2048,
        file_path: 'uploads/1/def.pdf',
        uploaded_at: '2026-01-01T00:00:00Z',
        processed: false,
      };

      vi.mocked(uploadResume).mockResolvedValueOnce(mockResume);

      const { result } = renderHook(() => useUploadResume(), { wrapper });

      const file = new File(['content'], 'new.pdf', { type: 'application/pdf' });

      result.current.mutate(file);

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(uploadResume).toHaveBeenCalledWith(file);
    });
  });

  describe('useDeleteResume', () => {
    it('should delete a resume and invalidate queries', async () => {
      vi.mocked(deleteResume).mockResolvedValueOnce(undefined);

      const { result } = renderHook(() => useDeleteResume(), { wrapper });

      result.current.mutate(1);

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(deleteResume).toHaveBeenCalledWith(1);
    });
  });
});
