import { useState } from 'react'
import { useSSETest } from '@/hooks/useSSETest'
import type { ConnectionStatus, SSEEvent } from '@/hooks/useSSETest'

function StatusDot({ status }: { status: ConnectionStatus }) {
  const colors: Record<ConnectionStatus, string> = {
    idle: 'bg-gray-400',
    connecting: 'bg-yellow-400 animate-pulse',
    connected: 'bg-green-500',
    reconnecting: 'bg-yellow-400 animate-pulse',
    disconnected: 'bg-gray-400',
    error: 'bg-red-500',
  }

  return (
    <span className={`inline-block w-3 h-3 rounded-full ${colors[status]}`} />
  )
}

function EventItem({ event }: { event: SSEEvent }) {
  const bgColors: Record<string, string> = {
    progress: 'bg-blue-50 border-blue-200',
    error: 'bg-red-50 border-red-200',
    complete: 'bg-green-50 border-green-200',
  }

  const time = new Date(event.receivedAt).toLocaleTimeString()

  return (
    <div className={`p-3 rounded border ${bgColors[event.type] || 'bg-gray-50 border-gray-200'}`}>
      <div className="flex items-center justify-between text-sm">
        <span className="font-mono font-semibold uppercase">{event.type}</span>
        <span className="text-gray-500">{time}</span>
      </div>
      {event.source && (
        <div className="text-sm text-gray-600 mt-1">Source: {event.source}</div>
      )}
      {event.message && (
        <div className="mt-1">{event.message}</div>
      )}
      {event.summary && (
        <div className="mt-1 font-semibold">{event.summary}</div>
      )}
      {event.type === 'error' && (
        <div className="text-xs mt-1 text-red-600">
          Recoverable: {event.recoverable ? 'yes' : 'no'}
        </div>
      )}
    </div>
  )
}

export function SSETestPage() {
  const [delay, setDelay] = useState(1000)
  const [errorAt, setErrorAt] = useState(0)
  const [fatalErrorAt, setFatalErrorAt] = useState(0)

  const { events, connectionStatus, isComplete, connect, reset } = useSSETest({
    delay,
    errorAt: errorAt || undefined,
    fatalErrorAt: fatalErrorAt || undefined,
  })

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">SSE Test Page</h1>
        <p className="text-gray-500 text-sm mt-1">
          Temporary page for Story 0-5 SSE proof-of-concept spike
        </p>
      </div>

      {/* Connection status */}
      <div className="flex items-center gap-2">
        <StatusDot status={connectionStatus} />
        <span className="text-sm font-medium capitalize">{connectionStatus}</span>
        {isComplete && <span className="text-sm text-green-600 ml-2">(Stream complete)</span>}
      </div>

      {/* Controls */}
      <div className="flex flex-wrap items-end gap-4">
        <div>
          <label className="block text-sm font-medium mb-1">Delay (ms)</label>
          <input
            type="number"
            value={delay}
            onChange={e => setDelay(Number(e.target.value))}
            className="border rounded px-2 py-1 w-24 text-sm"
            min={100}
            step={100}
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Error at event #</label>
          <input
            type="number"
            value={errorAt}
            onChange={e => setErrorAt(Number(e.target.value))}
            className="border rounded px-2 py-1 w-24 text-sm"
            min={0}
            max={5}
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Fatal error at #</label>
          <input
            type="number"
            value={fatalErrorAt}
            onChange={e => setFatalErrorAt(Number(e.target.value))}
            className="border rounded px-2 py-1 w-24 text-sm"
            min={0}
            max={5}
          />
        </div>
        <button
          onClick={connect}
          className="px-4 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
        >
          Start Stream
        </button>
        <button
          onClick={reset}
          className="px-4 py-1.5 bg-gray-200 text-gray-700 rounded text-sm hover:bg-gray-300"
        >
          Reset
        </button>
      </div>

      {/* Event list */}
      <div className="space-y-2">
        <div className="text-sm text-gray-500">
          Events received: {events.length}
        </div>
        <div className="space-y-2 max-h-[500px] overflow-y-auto">
          {events.map((event) => (
            <EventItem key={event.receivedAt} event={event} />
          ))}
        </div>
      </div>
    </div>
  )
}
