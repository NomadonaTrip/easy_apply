"""Rate pacing utility for LLM calls.

Enforces a minimum interval between consecutive LLM API calls
to avoid hitting rate limits proactively.
"""

import asyncio
from time import monotonic


class RatePacer:
    """Enforces minimum interval between LLM calls.

    Usage:
        pacer = RatePacer(min_interval_seconds=1.0)
        await pacer.pace()  # First call proceeds immediately
        await pacer.pace()  # Sleeps if less than 1.0s has elapsed
    """

    def __init__(self, min_interval_seconds: float = 1.0):
        self._min_interval = min_interval_seconds
        self._last_call_time: float | None = None
        self._lock = asyncio.Lock()

    async def pace(self) -> None:
        """Wait if needed to enforce minimum interval between calls."""
        async with self._lock:
            now = monotonic()
            if self._last_call_time is not None:
                elapsed = now - self._last_call_time
                if elapsed < self._min_interval:
                    await asyncio.sleep(self._min_interval - elapsed)
            self._last_call_time = monotonic()
