import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRoleStore } from '@/stores/roleStore';
import { getResumes, uploadResume, deleteResume, type Resume } from '@/api/resumes';

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

// Re-export types for convenience
export type { Resume };
