import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useResearchStream } from './useResearchStream';

// Mock roleStore
vi.mock('@/stores/roleStore', () => ({
  useRoleStore: {
    getState: () => ({ currentRole: { id: 1 } }),
  },
}));

// Mock fetch globally (already set up in test/setup.ts)
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Helper to create a mock SSE readable stream
function createMockSSEResponse(events: object[], options?: { delayBetween?: number }) {
  const encoder = new TextEncoder();
  let eventIndex = 0;

  const stream = new ReadableStream({
    async pull(controller) {
      if (eventIndex < events.length) {
        const event = events[eventIndex];
        const sseData = `data: ${JSON.stringify(event)}\n\n`;
        controller.enqueue(encoder.encode(sseData));
        eventIndex++;
        if (options?.delayBetween) {
          await new Promise((r) => setTimeout(r, options.delayBetween));
        }
      } else {
        controller.close();
      }
    },
  });

  return new Response(stream, {
    status: 200,
    headers: { 'Content-Type': 'text/event-stream' },
  });
}

describe('useResearchStream', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('initializes with 6 pending sources', () => {
    const { result } = renderHook(() => useResearchStream(1));

    expect(result.current.sources).toHaveLength(6);
    expect(result.current.sources.every((s) => s.status === 'pending')).toBe(true);
    expect(result.current.isComplete).toBe(false);
    expect(result.current.isError).toBe(false);
    expect(result.current.error).toBeNull();
    expect(result.current.progress).toBe(0);
  });

  it('has expected source names', () => {
    const { result } = renderHook(() => useResearchStream(1));

    const sourceNames = result.current.sources.map((s) => s.source);
    expect(sourceNames).toEqual([
      'strategic_initiatives',
      'competitive_landscape',
      'news_momentum',
      'industry_context',
      'culture_values',
      'leadership_direction',
    ]);
  });

  it('calls POST to start research then connects to SSE stream', async () => {
    // Mock POST response
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ status: 'started' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    // Mock SSE stream response
    const sseResponse = createMockSSEResponse([
      { type: 'progress', source: 'strategic_initiatives', status: 'searching', message: 'Researching...' },
      { type: 'complete', research_data: {}, gaps: [], categories_found: 6, categories_total: 6 },
    ]);
    mockFetch.mockResolvedValueOnce(sseResponse);

    const { result } = renderHook(() => useResearchStream(1));

    await act(async () => {
      result.current.startResearch();
      // Allow microtasks to process
      await new Promise((r) => setTimeout(r, 50));
    });

    // Should have called POST first, then GET for SSE
    expect(mockFetch).toHaveBeenCalledTimes(2);
    expect(mockFetch.mock.calls[0][0]).toBe('/api/v1/applications/1/research');
    expect(mockFetch.mock.calls[0][1]).toMatchObject({ method: 'POST' });
    expect(mockFetch.mock.calls[1][0]).toBe('/api/v1/applications/1/research/stream');
  });

  it('updates source status on progress events', async () => {
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ status: 'started' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    const sseResponse = createMockSSEResponse([
      { type: 'progress', source: 'strategic_initiatives', status: 'searching', message: 'Investigating strategic initiatives...' },
    ]);
    mockFetch.mockResolvedValueOnce(sseResponse);

    const { result } = renderHook(() => useResearchStream(1));

    await act(async () => {
      result.current.startResearch();
      await new Promise((r) => setTimeout(r, 50));
    });

    const strategicSource = result.current.sources.find((s) => s.source === 'strategic_initiatives');
    expect(strategicSource?.status).toBe('running');
    expect(strategicSource?.message).toBe('Investigating strategic initiatives...');
  });

  it('marks source complete when progress event has status "complete"', async () => {
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ status: 'started' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    const sseResponse = createMockSSEResponse([
      { type: 'progress', source: 'culture_values', status: 'complete', message: 'Culture analysis complete', found: true },
    ]);
    mockFetch.mockResolvedValueOnce(sseResponse);

    const { result } = renderHook(() => useResearchStream(1));

    await act(async () => {
      result.current.startResearch();
      await new Promise((r) => setTimeout(r, 50));
    });

    const cultureSource = result.current.sources.find((s) => s.source === 'culture_values');
    expect(cultureSource?.status).toBe('complete');
    expect(cultureSource?.found).toBe(true);
  });

  it('sets isComplete on complete event', async () => {
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ status: 'started' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    const sseResponse = createMockSSEResponse([
      { type: 'complete', research_data: {}, gaps: [], categories_found: 6, categories_total: 6 },
    ]);
    mockFetch.mockResolvedValueOnce(sseResponse);

    const { result } = renderHook(() => useResearchStream(1));

    await act(async () => {
      result.current.startResearch();
      await new Promise((r) => setTimeout(r, 50));
    });

    expect(result.current.isComplete).toBe(true);
  });

  it('marks gap sources as failed on complete event', async () => {
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ status: 'started' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    const sseResponse = createMockSSEResponse([
      { type: 'complete', research_data: {}, gaps: ['news_momentum', 'leadership_direction'], categories_found: 4, categories_total: 6 },
    ]);
    mockFetch.mockResolvedValueOnce(sseResponse);

    const { result } = renderHook(() => useResearchStream(1));

    await act(async () => {
      result.current.startResearch();
      await new Promise((r) => setTimeout(r, 50));
    });

    const newsSource = result.current.sources.find((s) => s.source === 'news_momentum');
    expect(newsSource?.status).toBe('failed');
    expect(newsSource?.found).toBe(false);

    const leadershipSource = result.current.sources.find((s) => s.source === 'leadership_direction');
    expect(leadershipSource?.status).toBe('failed');
    expect(leadershipSource?.found).toBe(false);

    // Non-gap sources should be complete
    const strategicSource = result.current.sources.find((s) => s.source === 'strategic_initiatives');
    expect(strategicSource?.status).toBe('complete');
    expect(strategicSource?.found).toBe(true);
  });

  it('calculates progress percentage correctly', async () => {
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ status: 'started' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    const sseResponse = createMockSSEResponse([
      { type: 'progress', source: 'strategic_initiatives', status: 'complete', found: true },
      { type: 'progress', source: 'competitive_landscape', status: 'complete', found: true },
      { type: 'progress', source: 'news_momentum', status: 'complete', found: false },
    ]);
    mockFetch.mockResolvedValueOnce(sseResponse);

    const { result } = renderHook(() => useResearchStream(1));

    await act(async () => {
      result.current.startResearch();
      await new Promise((r) => setTimeout(r, 50));
    });

    // 3/6 = 50%
    expect(result.current.progress).toBe(50);
  });

  it('handles error events', async () => {
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ status: 'started' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    const sseResponse = createMockSSEResponse([
      { type: 'error', message: 'LLM provider unavailable', recoverable: false },
    ]);
    mockFetch.mockResolvedValueOnce(sseResponse);

    const { result } = renderHook(() => useResearchStream(1));

    await act(async () => {
      result.current.startResearch();
      await new Promise((r) => setTimeout(r, 50));
    });

    expect(result.current.isError).toBe(true);
    expect(result.current.error).toBe('LLM provider unavailable');
  });

  it('handles POST failure', async () => {
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'Application not found' }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    const { result } = renderHook(() => useResearchStream(1));

    await act(async () => {
      result.current.startResearch();
      await new Promise((r) => setTimeout(r, 50));
    });

    expect(result.current.isError).toBe(true);
    expect(result.current.error).toBe('Application not found');
  });

  it('resets state on retryConnection', async () => {
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ status: 'started' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    const sseResponse = createMockSSEResponse([
      { type: 'error', message: 'Connection lost', recoverable: false },
    ]);
    mockFetch.mockResolvedValueOnce(sseResponse);

    const { result } = renderHook(() => useResearchStream(1));

    await act(async () => {
      result.current.startResearch();
      await new Promise((r) => setTimeout(r, 50));
    });

    expect(result.current.isError).toBe(true);

    // Set up the retry SSE response
    const retryResponse = createMockSSEResponse([
      { type: 'progress', source: 'strategic_initiatives', status: 'searching', message: 'Retrying...' },
    ]);
    mockFetch.mockResolvedValueOnce(retryResponse);

    await act(async () => {
      result.current.retryConnection();
      await new Promise((r) => setTimeout(r, 50));
    });

    expect(result.current.isError).toBe(false);
    expect(result.current.error).toBeNull();
  });
});
