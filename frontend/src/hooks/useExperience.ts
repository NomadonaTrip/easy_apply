import { useQuery } from '@tanstack/react-query';
import { useRoleStore } from '@/stores/roleStore';
import {
  getExperience,
  getSkills,
  getAccomplishments,
  getExperienceStats,
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
