"""SSE Manager for managing Server-Sent Event streams."""

import asyncio
import json
from typing import AsyncGenerator


class SSEManager:
    """Manages Server-Sent Event streams for research progress."""

    def __init__(self):
        self._streams: dict[int, asyncio.Queue] = {}
        self._active: dict[int, bool] = {}

    async def create_stream(self, application_id: int) -> AsyncGenerator[str, None]:
        """Create an SSE stream for an application's research."""
        if application_id not in self._streams:
            self._streams[application_id] = asyncio.Queue()
        self._active[application_id] = True

        try:
            while self._active.get(application_id, False):
                try:
                    event = await asyncio.wait_for(
                        self._streams[application_id].get(),
                        timeout=30.0,
                    )
                    yield f"data: {json.dumps(event)}\n\n"

                    if event.get("type") in ("complete", "error"):
                        break

                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"

        except asyncio.CancelledError:
            pass
        finally:
            self._cleanup(application_id)

    async def send_event(
        self,
        application_id: int,
        event_type: str,
        data: dict,
    ) -> None:
        """Send an event to an application's SSE stream."""
        if application_id not in self._streams:
            return

        event = {"type": event_type, **data}
        await self._streams[application_id].put(event)

    def close_stream(self, application_id: int) -> None:
        """Close an application's SSE stream."""
        self._active[application_id] = False

    def is_active(self, application_id: int) -> bool:
        """Check if a stream is active for an application."""
        return self._active.get(application_id, False)

    def _cleanup(self, application_id: int) -> None:
        """Clean up stream resources."""
        self._streams.pop(application_id, None)
        self._active.pop(application_id, None)


# Global singleton instance
sse_manager = SSEManager()
