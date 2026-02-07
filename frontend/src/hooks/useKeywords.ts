import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useRef } from 'react';
import { useRoleStore } from '@/stores/roleStore';
import { extractKeywords, saveKeywords } from '@/api/applications';
import type { Keyword } from '@/api/applications';

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

export function useSaveKeywords(applicationId: string) {
  const queryClient = useQueryClient();
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mutateRef = useRef<(keywords: Keyword[]) => void>();

  const mutation = useMutation({
    mutationFn: (keywords: Keyword[]) =>
      saveKeywords(Number(applicationId), keywords),
    onSuccess: (data) => {
      queryClient.setQueryData(['application', applicationId], data);
    },
  });

  // Keep ref pointing to latest mutate function
  useEffect(() => {
    mutateRef.current = mutation.mutate;
  }, [mutation.mutate]);

  const debouncedSave = useCallback(
    (keywords: Keyword[]) => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }

      debounceRef.current = setTimeout(() => {
        mutateRef.current?.(keywords);
      }, 300);
    },
    [],
  );

  // Clean up debounce timer on unmount only
  useEffect(() => {
    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, []);

  return {
    save: debouncedSave,
    isSaving: mutation.isPending,
    error: mutation.error,
  };
}
