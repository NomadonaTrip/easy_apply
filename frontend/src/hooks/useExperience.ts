import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRoleStore } from '@/stores/roleStore';
import {
  getExperience,
  getSkills,
  getAccomplishments,
  getExperienceStats,
  getEnrichmentCandidates,
  getEnrichmentStats,
  acceptCandidate,
  dismissCandidate,
  bulkResolve,
  triggerEnrichment,
} from '@/api/experience';

export function useExperience() {
  const roleId = useRoleStore((s) => s.currentRole?.id);

  return useQuery({
    queryKey: ['experience', roleId],
    queryFn: getExperience,
    enabled: !!roleId,
  });
}

export function useSkills() {
  const roleId = useRoleStore((s) => s.currentRole?.id);

  return useQuery({
    queryKey: ['skills', roleId],
    queryFn: getSkills,
    enabled: !!roleId,
  });
}

export function useAccomplishments() {
  const roleId = useRoleStore((s) => s.currentRole?.id);

  return useQuery({
    queryKey: ['accomplishments', roleId],
    queryFn: getAccomplishments,
    enabled: !!roleId,
  });
}

export function useExperienceStats() {
  const roleId = useRoleStore((s) => s.currentRole?.id);

  return useQuery({
    queryKey: ['experience-stats', roleId],
    queryFn: getExperienceStats,
    enabled: !!roleId,
  });
}

export function useEnrichmentCandidates() {
  const roleId = useRoleStore((s) => s.currentRole?.id);

  return useQuery({
    queryKey: ['enrichment-candidates', roleId],
    queryFn: getEnrichmentCandidates,
    enabled: !!roleId,
  });
}

export function useEnrichmentStats() {
  const roleId = useRoleStore((s) => s.currentRole?.id);

  return useQuery({
    queryKey: ['enrichment-stats', roleId],
    queryFn: getEnrichmentStats,
    enabled: !!roleId,
  });
}

export function useAcceptCandidate() {
  const queryClient = useQueryClient();
  const roleId = useRoleStore((s) => s.currentRole?.id);

  return useMutation({
    mutationFn: (candidateId: number) => acceptCandidate(candidateId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['enrichment-candidates', roleId] });
      queryClient.invalidateQueries({ queryKey: ['enrichment-stats', roleId] });
      queryClient.invalidateQueries({ queryKey: ['experience', roleId] });
      queryClient.invalidateQueries({ queryKey: ['skills', roleId] });
      queryClient.invalidateQueries({ queryKey: ['accomplishments', roleId] });
    },
  });
}

export function useDismissCandidate() {
  const queryClient = useQueryClient();
  const roleId = useRoleStore((s) => s.currentRole?.id);

  return useMutation({
    mutationFn: (candidateId: number) => dismissCandidate(candidateId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['enrichment-candidates', roleId] });
      queryClient.invalidateQueries({ queryKey: ['enrichment-stats', roleId] });
    },
  });
}

export function useBulkResolve() {
  const queryClient = useQueryClient();
  const roleId = useRoleStore((s) => s.currentRole?.id);

  return useMutation({
    mutationFn: ({ ids, action }: { ids: number[]; action: 'accept' | 'dismiss' }) =>
      bulkResolve(ids, action),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['enrichment-candidates', roleId] });
      queryClient.invalidateQueries({ queryKey: ['enrichment-stats', roleId] });
      queryClient.invalidateQueries({ queryKey: ['experience', roleId] });
      queryClient.invalidateQueries({ queryKey: ['skills', roleId] });
      queryClient.invalidateQueries({ queryKey: ['accomplishments', roleId] });
    },
  });
}

export function useTriggerEnrichment() {
  const queryClient = useQueryClient();
  const roleId = useRoleStore((s) => s.currentRole?.id);

  return useMutation({
    mutationFn: (applicationId: number) => triggerEnrichment(applicationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['enrichment-candidates', roleId] });
      queryClient.invalidateQueries({ queryKey: ['enrichment-stats', roleId] });
    },
  });
}
