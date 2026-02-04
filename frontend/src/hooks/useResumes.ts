import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRoleStore } from '@/stores/roleStore';
import {
  getResumes,
  uploadResume,
  deleteResume,
  extractFromResume,
  extractAllResumes,
  type Resume,
  type ExtractionResult,
  type BulkExtractionResult,
} from '@/api/resumes';

/**
 * Hook to fetch all resumes for the current role.
 */
export function useResumes() {
  const roleId = useRoleStore((s) => s.currentRole?.id);

  return useQuery({
    queryKey: ['resumes', roleId],
    queryFn: getResumes,
    enabled: !!roleId,
  });
}

/**
 * Hook to upload a resume.
 * Automatically invalidates the resumes query on success.
 */
export function useUploadResume() {
  const queryClient = useQueryClient();
  const roleId = useRoleStore((s) => s.currentRole?.id);

  return useMutation({
    mutationFn: (file: File) => uploadResume(file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['resumes', roleId] });
    },
  });
}

/**
 * Hook to delete a resume.
 * Automatically invalidates the resumes query on success.
 */
export function useDeleteResume() {
  const queryClient = useQueryClient();
  const roleId = useRoleStore((s) => s.currentRole?.id);

  return useMutation({
    mutationFn: (resumeId: number) => deleteResume(resumeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['resumes', roleId] });
    },
  });
}

/**
 * Hook to extract skills and accomplishments from a single resume.
 * Automatically invalidates resumes, skills, accomplishments, and experience queries on success.
 */
export function useExtractFromResume() {
  const queryClient = useQueryClient();
  const roleId = useRoleStore((s) => s.currentRole?.id);

  return useMutation({
    mutationFn: (resumeId: number) => extractFromResume(resumeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['resumes', roleId] });
      queryClient.invalidateQueries({ queryKey: ['skills', roleId] });
      queryClient.invalidateQueries({ queryKey: ['accomplishments', roleId] });
      queryClient.invalidateQueries({ queryKey: ['experience', roleId] });
      queryClient.invalidateQueries({ queryKey: ['experience-stats', roleId] });
    },
  });
}

/**
 * Hook to extract skills and accomplishments from all unprocessed resumes.
 * Automatically invalidates resumes, skills, accomplishments, and experience queries on success.
 */
export function useExtractAllResumes() {
  const queryClient = useQueryClient();
  const roleId = useRoleStore((s) => s.currentRole?.id);

  return useMutation({
    mutationFn: extractAllResumes,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['resumes', roleId] });
      queryClient.invalidateQueries({ queryKey: ['skills', roleId] });
      queryClient.invalidateQueries({ queryKey: ['accomplishments', roleId] });
      queryClient.invalidateQueries({ queryKey: ['experience', roleId] });
      queryClient.invalidateQueries({ queryKey: ['experience-stats', roleId] });
    },
  });
}

// Re-export types for convenience
export type { Resume, ExtractionResult, BulkExtractionResult };
