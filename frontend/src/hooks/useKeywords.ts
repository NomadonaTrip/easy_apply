import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useRoleStore } from '@/stores/roleStore';
import { extractKeywords } from '@/api/applications';

export function useExtractKeywords() {
  const queryClient = useQueryClient();
  const roleId = useRoleStore((s) => s.currentRole?.id);

  return useMutation({
    mutationFn: (applicationId: number) => extractKeywords(applicationId),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['applications', roleId] });
      queryClient.invalidateQueries({ queryKey: ['application', String(data.application_id)] });
    },
  });
}
