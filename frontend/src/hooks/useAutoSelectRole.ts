import { useEffect, useRef } from 'react';
import { useRoles } from '@/hooks/useRoles';
import { useRoleStore } from '@/stores/roleStore';

/**
 * Hook to auto-select a role when the user has roles but none is selected.
 *
 * Behavior:
 * - If user has roles and no current role, auto-select the first role
 * - If user has roles and current role exists but is not in the list, reset to first role
 * - If user has no roles, returns needsRoleCreation: true
 *
 * @returns Object with needsRoleCreation flag
 */
export function useAutoSelectRole() {
  const { data: roles, isSuccess } = useRoles();
  const { currentRole, setCurrentRole } = useRoleStore();
  const hasInitialized = useRef(false);

  useEffect(() => {
    if (!isSuccess || !roles) return;

    // No roles available
    if (roles.length === 0) {
      hasInitialized.current = true;
      return;
    }

    // No role currently selected - auto-select first
    if (!currentRole) {
      setCurrentRole(roles[0]);
      hasInitialized.current = true;
      return;
    }

    // Check if current role still exists in the list (handles deleted roles)
    const roleStillExists = roles.some((r) => r.id === currentRole.id);
    if (!roleStillExists) {
      setCurrentRole(roles[0]);
    }
    hasInitialized.current = true;
  }, [isSuccess, roles, currentRole, setCurrentRole]);

  return {
    needsRoleCreation: isSuccess && (!roles || roles.length === 0),
  };
}
