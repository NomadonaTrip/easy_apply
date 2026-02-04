import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { queryClient } from '@/lib/queryClient';
import type { Role } from '@/api/types';

export type { Role };

interface RoleState {
  currentRole: Role | null;
  setCurrentRole: (role: Role) => void;
  clearCurrentRole: () => void;
}

export const useRoleStore = create<RoleState>()(
  persist(
    (set) => ({
      currentRole: null,
      setCurrentRole: (role) => {
        set({ currentRole: role });

        // Invalidate all role-scoped queries when role changes
        // These query keys contain role-scoped data that needs refresh
        queryClient.invalidateQueries({ queryKey: ['applications'] });
        queryClient.invalidateQueries({ queryKey: ['skills'] });
        queryClient.invalidateQueries({ queryKey: ['accomplishments'] });
        queryClient.invalidateQueries({ queryKey: ['experience'] });
        queryClient.invalidateQueries({ queryKey: ['resumes'] });
      },
      clearCurrentRole: () => {
        set({ currentRole: null });

        // Clear all cached data on logout/role clear
        queryClient.clear();
      },
    }),
    {
      name: 'role-storage', // localStorage key
      partialize: (state) => ({ currentRole: state.currentRole }),
    }
  )
);
