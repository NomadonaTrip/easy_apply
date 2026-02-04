import { describe, it, expect, beforeEach, vi } from 'vitest';
import { uploadResume, getResumes, deleteResume } from './resumes';
import { useRoleStore } from '@/stores/roleStore';

// Mock fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Mock role store
vi.mock('@/stores/roleStore', () => ({
  useRoleStore: {
    getState: vi.fn(() => ({
      currentRole: { id: 1, user_id: 1, name: 'Test Role', created_at: '2026-01-01' },
    })),
  },
}));

describe('resumes API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('uploadResume', () => {
    it('should upload a file and return resume data', async () => {
      const mockResume = {
        id: 1,
        role_id: 1,
        filename: 'resume.pdf',
        file_type: 'pdf',
        file_size: 1024,
        file_path: 'uploads/1/abc.pdf',
        uploaded_at: '2026-01-01T00:00:00Z',
        processed: false,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: () => Promise.resolve(mockResume),
      });

      const file = new File(['content'], 'resume.pdf', { type: 'application/pdf' });
      const result = await uploadResume(file);

      expect(result).toEqual(mockResume);
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/resumes/upload',
        expect.objectContaining({
          method: 'POST',
          credentials: 'include',
          headers: {
            'X-Role-Id': '1',
          },
        })
      );
    });

    it('should throw error when no role selected', async () => {
      vi.mocked(useRoleStore.getState).mockReturnValueOnce({
        currentRole: null,
        setCurrentRole: vi.fn(),
        clearCurrentRole: vi.fn(),
      });

      const file = new File(['content'], 'resume.pdf', { type: 'application/pdf' });

      await expect(uploadResume(file)).rejects.toThrow('No role selected');
    });

    it('should throw error on upload failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: () => Promise.resolve({ detail: 'Invalid file type' }),
      });

      const file = new File(['content'], 'resume.txt', { type: 'text/plain' });

      await expect(uploadResume(file)).rejects.toThrow('Invalid file type');
    });
  });

  describe('getResumes', () => {
    it('should fetch resumes for current role', async () => {
      const mockResumes = [
        {
          id: 1,
          role_id: 1,
          filename: 'resume1.pdf',
          file_type: 'pdf',
          file_size: 1024,
          file_path: 'uploads/1/abc.pdf',
          uploaded_at: '2026-01-01T00:00:00Z',
          processed: false,
        },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockResumes),
      });

      const result = await getResumes();

      expect(result).toEqual(mockResumes);
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/resumes',
        expect.objectContaining({
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json',
            'X-Role-Id': '1',
          },
        })
      );
    });
  });

  describe('deleteResume', () => {
    it('should delete a resume', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 204,
      });

      await deleteResume(1);

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/resumes/1',
        expect.objectContaining({
          method: 'DELETE',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json',
            'X-Role-Id': '1',
          },
        })
      );
    });

    it('should throw error on delete failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: () => Promise.resolve({ detail: 'Resume not found' }),
      });

      await expect(deleteResume(999)).rejects.toThrow('Resume not found');
    });
  });
});
