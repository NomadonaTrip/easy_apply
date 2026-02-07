"""Circuit breaker utility for LLM calls.

Tracks consecutive failures and opens the circuit to prevent
cascading failures when the LLM provider is unhealthy.
"""

from time import monotonic


class CircuitOpenError(Exception):
    """Raised when a call is attempted while the circuit is open."""

    pass


class CircuitBreaker:
    """Circuit breaker with closed/open/half-open states.

    States:
        - closed: Normal operation, calls proceed
        - open: Too many failures, calls blocked (raises CircuitOpenError)
        - half-open: After reset_timeout, allows one test call

    Usage:
        cb = CircuitBreaker(failure_threshold=3, reset_timeout=60.0)
        if cb.can_proceed():
            try:
                result = await make_call()
                cb.record_success()
            except Exception:
                cb.record_failure()
    """

    def __init__(
        self, failure_threshold: int = 3, reset_timeout: float = 60.0
    ):
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._failure_count = 0
        self._state = "closed"
        self._last_failure_time: float | None = None

    def can_proceed(self) -> bool:
        """Check if a call can proceed through the circuit.

        Returns True if circuit is closed or transitioning to half-open.
        Returns False if circuit is open and timeout hasn't elapsed.
        """
        if self._state == "closed":
            return True

        if self._state == "open":
            if self._last_failure_time is not None:
                elapsed = monotonic() - self._last_failure_time
                if elapsed >= self._reset_timeout:
                    self._state = "half-open"
                    return True
            return False

        # half-open: allow one test call
        return True

    def record_success(self) -> None:
        """Record a successful call. Resets failure count and closes circuit."""
        self._failure_count = 0
        self._state = "closed"

    def record_failure(self) -> None:
        """Record a failed call. Opens circuit if threshold reached."""
        self._failure_count = min(self._failure_count + 1, self._failure_threshold)
        self._last_failure_time = monotonic()
        if self._failure_count >= self._failure_threshold:
            self._state = "open"
