import { useState, useEffect, useCallback, useRef } from 'react';
import { startResearch as startResearchApi } from '@/api/applications';
import { useRoleStore } from '@/stores/roleStore';

export type ResearchSourceStatus = 'pending' | 'running' | 'complete' | 'failed';

export interface ResearchSourceState {
  source: string;
  status: ResearchSourceStatus;
  message?: string;
  found?: boolean;
}

export interface UseResearchStreamReturn {
  sources: ResearchSourceState[];
  isComplete: boolean;
  isError: boolean;
  error: string | null;
  progress: number;
  startResearch: () => void;
  retryConnection: () => void;
}

const RESEARCH_CATEGORIES = [
  { source: 'strategic_initiatives', label: 'Strategic Initiatives' },
  { source: 'competitive_landscape', label: 'Competitive Landscape' },
  { source: 'news_momentum', label: 'Recent News & Momentum' },
  { source: 'industry_context', label: 'Industry Context' },
  { source: 'culture_values', label: 'Culture & Values' },
  { source: 'leadership_direction', label: 'Leadership Direction' },
] as const;

export { RESEARCH_CATEGORIES };

export function useResearchStream(applicationId: number): UseResearchStreamReturn {
  const [sources, setSources] = useState<ResearchSourceState[]>(
    RESEARCH_CATEGORIES.map((s) => ({ source: s.source, status: 'pending' as const })),
  );
  const [isComplete, setIsComplete] = useState(false);
  const [isError, setIsError] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const connectToStream = useCallback(() => {
    // Abort any existing connection
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    const { currentRole } = useRoleStore.getState();
    const headers: Record<string, string> = {};
    if (currentRole) {
      headers['X-Role-Id'] = currentRole.id.toString();
    }

    function handleEvent(data: Record<string, unknown>) {
      if (data.type === 'progress') {
        setSources((prev) =>
          prev.map((s) =>
            s.source === data.source
              ? {
                  ...s,
                  status: data.status === 'complete' ? ('complete' as const) : ('running' as const),
                  message: data.message as string | undefined,
                  found: (data.found as boolean | undefined) ?? true,
                }
              : s,
          ),
        );
      } else if (data.type === 'complete') {
        setIsComplete(true);
        const gaps = (data.gaps as string[]) || [];
        setSources((prev) =>
          prev.map((s) =>
            gaps.includes(s.source)
              ? { ...s, status: 'failed' as const, found: false }
              : { ...s, status: 'complete' as const, found: true },
          ),
        );
        abortController.abort();
      } else if (data.type === 'error') {
        setIsError(true);
        setError((data.message as string) || 'An error occurred during research');
        abortController.abort();
      }
    }

    // Raw fetch required: SSE streaming needs ReadableStream access
    // (apiRequest parses responses as JSON, incompatible with SSE)
    fetch(`/api/v1/applications/${applicationId}/research/stream`, {
      credentials: 'include',
      headers,
      signal: abortController.signal,
    })
      .then(async (response) => {
        if (!response.ok) {
          const data = await response.json().catch(() => ({ detail: 'Stream connection failed' }));
          setIsError(true);
          setError(typeof data.detail === 'string' ? data.detail : 'Stream connection failed');
          return;
        }

        const reader = response.body?.getReader();
        if (!reader) {
          setIsError(true);
          setError('Stream not available');
          return;
        }

        const decoder = new TextDecoder();
        let buffer = '';

        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            // Parse SSE events from buffer
            const lines = buffer.split('\n');
            buffer = lines.pop() || ''; // Keep incomplete line in buffer

            for (const line of lines) {
              if (line.startsWith('data: ')) {
                const jsonStr = line.slice(6).trim();
                if (!jsonStr) continue;

                try {
                  const data = JSON.parse(jsonStr);
                  handleEvent(data);
                } catch {
                  console.error('Failed to parse SSE event:', jsonStr);
                }
              }
              // Ignore comment lines (keepalive) and empty lines
            }
          }
        } catch (err) {
          if (err instanceof Error && err.name === 'AbortError') {
            return; // Expected during cleanup
          }
          setIsError(true);
          setError('Connection lost. Click retry to reconnect.');
        }
      })
      .catch((err) => {
        if (err instanceof Error && err.name === 'AbortError') {
          return; // Expected during cleanup
        }
        setIsError(true);
        setError('Connection lost. Click retry to reconnect.');
      });
  }, [applicationId]);

  const startResearch = useCallback(async () => {
    // Reset state
    setSources(RESEARCH_CATEGORIES.map((s) => ({ source: s.source, status: 'pending' as const })));
    setIsComplete(false);
    setIsError(false);
    setError(null);

    try {
      await startResearchApi(applicationId);
      connectToStream();
    } catch (e) {
      setIsError(true);
      setError(e instanceof Error ? e.message : 'Failed to start research');
    }
  }, [applicationId, connectToStream]);

  const retryConnection = useCallback(() => {
    setIsError(false);
    setError(null);
    connectToStream();
  }, [connectToStream]);

  // Calculate progress percentage
  const progress = Math.round(
    (sources.filter((s) => s.status === 'complete' || s.status === 'failed').length / sources.length) * 100,
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  return {
    sources,
    isComplete,
    isError,
    error,
    progress,
    startResearch,
    retryConnection,
  };
}
