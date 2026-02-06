import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRoleStore } from '@/stores/roleStore';
import { getApplications, createApplication } from '@/api/applications';
import type { ApplicationCreate } from '@/api/applications';

export function useApplications() {
  const roleId = useRoleStore((s) => s.currentRole?.id);

  return useQuery({
    queryKey: ['applications', roleId],
    queryFn: getApplications,
    enabled: !!roleId,
  });
}

export function useCreateApplication() {
  const queryClient = useQueryClient();
  const roleId = useRoleStore((s) => s.currentRole?.id);

  return useMutation({
    mutationFn: (data: ApplicationCreate) => createApplication(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['applications', roleId] });
    },
  });
}
