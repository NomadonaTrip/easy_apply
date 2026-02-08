import { useState, useEffect, useCallback, useRef } from 'react'

export type ConnectionStatus = 'idle' | 'connecting' | 'connected' | 'reconnecting' | 'disconnected' | 'error'

export interface SSEEvent {
  type: 'progress' | 'error' | 'complete'
  source?: string
  status?: string
  message?: string
  summary?: string
  recoverable?: boolean
  receivedAt: number
}

interface UseSSETestOptions {
  delay?: number
  errorAt?: number
  fatalErrorAt?: number
}

export function useSSETest(options: UseSSETestOptions = {}) {
  const [events, setEvents] = useState<SSEEvent[]>([])
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('idle')
  const [isComplete, setIsComplete] = useState(false)
  const eventSourceRef = useRef<EventSource | null>(null)

  /** Opens a new SSE connection. Closes any existing connection first.
   *  Options are captured at call time — changing options requires a new connect() call. */
  const connect = useCallback(() => {
    // Close existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
    }

    setEvents([])
    setIsComplete(false)
    setConnectionStatus('connecting')

    const params = new URLSearchParams()
    if (options.delay) params.set('delay', String(options.delay))
    if (options.errorAt) params.set('error_at', String(options.errorAt))
    if (options.fatalErrorAt) params.set('fatal_error_at', String(options.fatalErrorAt))

    const url = `/api/v1/test/sse${params.toString() ? '?' + params.toString() : ''}`
    const es = new EventSource(url)
    eventSourceRef.current = es

    es.onopen = () => {
      setConnectionStatus('connected')
    }

    es.onmessage = (event) => {
      let data: Omit<SSEEvent, 'receivedAt'>
      try {
        data = JSON.parse(event.data)
      } catch {
        console.warn('SSE: Failed to parse event data:', event.data)
        return
      }
      const sseEvent: SSEEvent = { ...data, receivedAt: Date.now() }

      setEvents(prev => [...prev, sseEvent])

      if (data.type === 'complete') {
        setIsComplete(true)
        es.close()
        setConnectionStatus('disconnected')
      }

      if (data.type === 'error' && data.recoverable === false) {
        es.close()
        setConnectionStatus('error')
      }
    }

    es.onerror = () => {
      if (es.readyState === EventSource.CONNECTING) {
        setConnectionStatus('reconnecting')
      } else if (es.readyState === EventSource.CLOSED) {
        setConnectionStatus('disconnected')
      }
    }
  }, [options.delay, options.errorAt, options.fatalErrorAt])

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
    setConnectionStatus('disconnected')
  }, [])

  const reset = useCallback(() => {
    disconnect()
    setEvents([])
    setIsComplete(false)
    setConnectionStatus('idle')
  }, [disconnect])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }
    }
  }, [])

  return {
    events,
    connectionStatus,
    isComplete,
    connect,
    disconnect,
    reset,
  }
}
