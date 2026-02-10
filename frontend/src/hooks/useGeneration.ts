import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useRoleStore } from '@/stores/roleStore';
import { generateResume } from '@/api/generation';

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
