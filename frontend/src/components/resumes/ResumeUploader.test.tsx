import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ResumeUploader } from './ResumeUploader';

// Mock the hooks
vi.mock('@/hooks/useResumes', () => ({
  useResumes: vi.fn(),
  useUploadResume: vi.fn(),
  useDeleteResume: vi.fn(),
  useExtractAllResumes: vi.fn(),
}));

import { useResumes, useUploadResume, useDeleteResume, useExtractAllResumes } from '@/hooks/useResumes';

describe('ResumeUploader', () => {
  let queryClient: QueryClient;

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
    {
      id: 2,
      role_id: 1,
      filename: 'resume2.docx',
      file_type: 'docx',
      file_size: 2048,
      file_path: 'uploads/1/def.docx',
      uploaded_at: '2026-01-02T00:00:00Z',
      processed: true,
    },
  ];

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });

    // Default mock implementations
    vi.mocked(useResumes).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
      error: null,
    } as ReturnType<typeof useResumes>);

    vi.mocked(useUploadResume).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useUploadResume>);

    vi.mocked(useDeleteResume).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useDeleteResume>);

    vi.mocked(useExtractAllResumes).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useExtractAllResumes>);
  });

  describe('Dropzone rendering', () => {
    it('should render upload dropzone', () => {
      render(<ResumeUploader />, { wrapper });

      expect(screen.getByText(/drag & drop resume files/i)).toBeInTheDocument();
      expect(screen.getByText(/pdf or docx, max 10mb/i)).toBeInTheDocument();
    });

    it('should have correct aria-label on file input for accessibility', () => {
      render(<ResumeUploader />, { wrapper });

      const input = screen.getByLabelText(/upload resume file/i);
      expect(input).toBeInTheDocument();
      expect(input).toHaveAttribute('type', 'file');
    });
  });

  describe('Loading states', () => {
    it('should show loading spinner while fetching resumes', () => {
      vi.mocked(useResumes).mockReturnValue({
        data: undefined,
        isLoading: true,
        isError: false,
        error: null,
      } as ReturnType<typeof useResumes>);

      render(<ResumeUploader />, { wrapper });

      expect(screen.getByText(/loading resumes/i)).toBeInTheDocument();
    });

    it('should show uploading state during file upload', () => {
      vi.mocked(useUploadResume).mockReturnValue({
        mutateAsync: vi.fn(),
        isPending: true,
      } as unknown as ReturnType<typeof useUploadResume>);

      render(<ResumeUploader />, { wrapper });

      expect(screen.getByText(/uploading/i)).toBeInTheDocument();
    });
  });

  describe('Resume list display', () => {
    it('should display uploaded resumes list', () => {
      vi.mocked(useResumes).mockReturnValue({
        data: mockResumes,
        isLoading: false,
        isError: false,
        error: null,
      } as ReturnType<typeof useResumes>);

      render(<ResumeUploader />, { wrapper });

      expect(screen.getByText('resume1.pdf')).toBeInTheDocument();
      expect(screen.getByText('resume2.docx')).toBeInTheDocument();
      expect(screen.getByText(/1.0 KB/)).toBeInTheDocument();
      expect(screen.getByText(/2.0 KB/)).toBeInTheDocument();
    });

    it('should show processed indicator for processed resumes', () => {
      vi.mocked(useResumes).mockReturnValue({
        data: mockResumes,
        isLoading: false,
        isError: false,
        error: null,
      } as ReturnType<typeof useResumes>);

      render(<ResumeUploader />, { wrapper });

      // resume2 is processed
      expect(screen.getByText(/processed/i)).toBeInTheDocument();
    });

    it('should show empty state when no resumes uploaded', () => {
      vi.mocked(useResumes).mockReturnValue({
        data: [],
        isLoading: false,
        isError: false,
        error: null,
      } as ReturnType<typeof useResumes>);

      render(<ResumeUploader />, { wrapper });

      expect(screen.getByText(/no resumes uploaded yet/i)).toBeInTheDocument();
    });
  });

  describe('Delete functionality', () => {
    it('should call delete mutation when delete button clicked', async () => {
      const mockDelete = vi.fn();
      vi.mocked(useResumes).mockReturnValue({
        data: mockResumes,
        isLoading: false,
        isError: false,
        error: null,
      } as ReturnType<typeof useResumes>);

      vi.mocked(useDeleteResume).mockReturnValue({
        mutate: mockDelete,
        isPending: false,
      } as unknown as ReturnType<typeof useDeleteResume>);

      render(<ResumeUploader />, { wrapper });

      // Click delete button for first resume
      const deleteButtons = screen.getAllByRole('button', { name: /delete/i });
      await userEvent.click(deleteButtons[0]);

      expect(mockDelete).toHaveBeenCalledWith(1);
    });

    it('should have accessible delete button with filename', () => {
      vi.mocked(useResumes).mockReturnValue({
        data: mockResumes,
        isLoading: false,
        isError: false,
        error: null,
      } as ReturnType<typeof useResumes>);

      render(<ResumeUploader />, { wrapper });

      expect(screen.getByRole('button', { name: /delete resume1\.pdf/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /delete resume2\.docx/i })).toBeInTheDocument();
    });
  });

  describe('Upload functionality', () => {
    it('should call upload mutation when files dropped', async () => {
      const mockUpload = vi.fn().mockResolvedValue(mockResumes[0]);
      vi.mocked(useUploadResume).mockReturnValue({
        mutateAsync: mockUpload,
        isPending: false,
      } as unknown as ReturnType<typeof useUploadResume>);

      render(<ResumeUploader />, { wrapper });

      const input = screen.getByLabelText(/upload resume file/i);
      const file = new File(['test'], 'test.pdf', { type: 'application/pdf' });

      await userEvent.upload(input, file);

      await waitFor(() => {
        expect(mockUpload).toHaveBeenCalledWith(file);
      });
    });
  });

  describe('Error handling', () => {
    it('should show error message when upload fails', async () => {
      const mockUpload = vi.fn().mockRejectedValue(new Error('Upload failed'));
      vi.mocked(useUploadResume).mockReturnValue({
        mutateAsync: mockUpload,
        isPending: false,
      } as unknown as ReturnType<typeof useUploadResume>);

      render(<ResumeUploader />, { wrapper });

      const input = screen.getByLabelText(/upload resume file/i);
      const file = new File(['test'], 'test.pdf', { type: 'application/pdf' });

      await userEvent.upload(input, file);

      await waitFor(() => {
        expect(screen.getByText(/upload failed/i)).toBeInTheDocument();
      });
    });
  });

  describe('File type validation', () => {
    it('should only accept PDF and DOCX files', () => {
      render(<ResumeUploader />, { wrapper });

      const input = screen.getByLabelText(/upload resume file/i);
      expect(input).toHaveAttribute('accept');
      // react-dropzone sets accept attribute
    });
  });

  describe('Extraction functionality', () => {
    it('should show extract button when unprocessed resumes exist', () => {
      vi.mocked(useResumes).mockReturnValue({
        data: mockResumes, // mockResumes[0] has processed: false
        isLoading: false,
        isError: false,
        error: null,
      } as ReturnType<typeof useResumes>);

      render(<ResumeUploader />, { wrapper });

      expect(screen.getByRole('button', { name: /extract skills from all resumes/i })).toBeInTheDocument();
    });

    it('should hide extract button when all resumes are processed', () => {
      const allProcessedResumes = mockResumes.map(r => ({ ...r, processed: true }));
      vi.mocked(useResumes).mockReturnValue({
        data: allProcessedResumes,
        isLoading: false,
        isError: false,
        error: null,
      } as ReturnType<typeof useResumes>);

      render(<ResumeUploader />, { wrapper });

      expect(screen.queryByRole('button', { name: /extract skills from all resumes/i })).not.toBeInTheDocument();
    });

    it('should call extract mutation when extract button clicked', async () => {
      const mockExtract = vi.fn().mockResolvedValue({
        message: '5 skills identified. 3 accomplishments extracted.',
        resumes_processed: 1,
        total_skills: 5,
        total_accomplishments: 3,
      });

      vi.mocked(useResumes).mockReturnValue({
        data: mockResumes,
        isLoading: false,
        isError: false,
        error: null,
      } as ReturnType<typeof useResumes>);

      vi.mocked(useExtractAllResumes).mockReturnValue({
        mutateAsync: mockExtract,
        isPending: false,
      } as unknown as ReturnType<typeof useExtractAllResumes>);

      render(<ResumeUploader />, { wrapper });

      const extractButton = screen.getByRole('button', { name: /extract skills from all resumes/i });
      await userEvent.click(extractButton);

      await waitFor(() => {
        expect(mockExtract).toHaveBeenCalled();
      });
    });

    it('should display extraction result message on success', async () => {
      const mockExtract = vi.fn().mockResolvedValue({
        message: '5 skills identified. 3 accomplishments extracted.',
        resumes_processed: 1,
        total_skills: 5,
        total_accomplishments: 3,
      });

      vi.mocked(useResumes).mockReturnValue({
        data: mockResumes,
        isLoading: false,
        isError: false,
        error: null,
      } as ReturnType<typeof useResumes>);

      vi.mocked(useExtractAllResumes).mockReturnValue({
        mutateAsync: mockExtract,
        isPending: false,
      } as unknown as ReturnType<typeof useExtractAllResumes>);

      render(<ResumeUploader />, { wrapper });

      const extractButton = screen.getByRole('button', { name: /extract skills from all resumes/i });
      await userEvent.click(extractButton);

      await waitFor(() => {
        expect(screen.getByText(/5 skills identified/i)).toBeInTheDocument();
      });
    });

    it('should display error message on extraction failure', async () => {
      const mockExtract = vi.fn().mockRejectedValue(new Error('Extraction failed'));

      vi.mocked(useResumes).mockReturnValue({
        data: mockResumes,
        isLoading: false,
        isError: false,
        error: null,
      } as ReturnType<typeof useResumes>);

      vi.mocked(useExtractAllResumes).mockReturnValue({
        mutateAsync: mockExtract,
        isPending: false,
      } as unknown as ReturnType<typeof useExtractAllResumes>);

      render(<ResumeUploader />, { wrapper });

      const extractButton = screen.getByRole('button', { name: /extract skills from all resumes/i });
      await userEvent.click(extractButton);

      await waitFor(() => {
        expect(screen.getByText(/extraction failed/i)).toBeInTheDocument();
      });
    });

    it('should show loading state during extraction', () => {
      vi.mocked(useResumes).mockReturnValue({
        data: mockResumes,
        isLoading: false,
        isError: false,
        error: null,
      } as ReturnType<typeof useResumes>);

      vi.mocked(useExtractAllResumes).mockReturnValue({
        mutateAsync: vi.fn(),
        isPending: true,
      } as unknown as ReturnType<typeof useExtractAllResumes>);

      render(<ResumeUploader />, { wrapper });

      expect(screen.getByText(/extracting skills/i)).toBeInTheDocument();
    });
  });
});
