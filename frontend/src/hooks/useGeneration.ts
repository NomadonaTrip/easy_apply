import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useRoleStore } from '@/stores/roleStore';
import { generateResume, generateCoverLetter } from '@/api/generation';
import type { CoverLetterTone } from '@/api/applications';

export function useGenerateResume() {
  const queryClient = useQueryClient();
  const roleId = useRoleStore((s) => s.currentRole?.id);

  return useMutation({
    mutationFn: (applicationId: number) => generateResume(applicationId),
    onSuccess: (_data, applicationId) => {
      queryClient.invalidateQueries({ queryKey: ['applications', roleId] });
      queryClient.invalidateQueries({ queryKey: ['application', applicationId] });
      queryClient.invalidateQueries({ queryKey: ['generation-status', applicationId] });
    },
  });
}

export function useGenerateCoverLetter() {
  const queryClient = useQueryClient();
  const roleId = useRoleStore((s) => s.currentRole?.id);

  return useMutation({
    mutationFn: ({ applicationId, tone }: { applicationId: number; tone: CoverLetterTone }) =>
      generateCoverLetter(applicationId, tone),
    onSuccess: (_data, { applicationId }) => {
      queryClient.invalidateQueries({ queryKey: ['applications', roleId] });
      queryClient.invalidateQueries({ queryKey: ['application', applicationId] });
      queryClient.invalidateQueries({ queryKey: ['generation-status', applicationId] });
    },
  });
}
