"""LLM call logging models for observability."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from sqlmodel import Field, SQLModel


class LLMCallLog(SQLModel, table=True):
    """SQLModel table for persisting LLM call records to SQLite.

    Optional storage - failures to persist do not affect LLM call results.
    """

    __tablename__ = "llm_call_log"

    id: Optional[int] = Field(default=None, primary_key=True)
    call_id: str = Field(index=True)
    timestamp: str  # ISO format UTC datetime string
    provider: str
    model: str
    prompt_name: Optional[str] = Field(default=None)
    prompt_tokens: Optional[int] = Field(default=None)
    response_tokens: Optional[int] = Field(default=None)
    latency_ms: int = Field(default=0)
    status: str  # "success", "error", "rate_limited", "timeout"
    error_message: Optional[str] = Field(default=None)
    application_id: Optional[int] = Field(default=None)
    role_id: Optional[int] = Field(default=None)

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        if not self.call_id or len(self.call_id.strip()) < 1:
            raise ValueError("call_id cannot be empty")
        if not self.provider or len(self.provider.strip()) < 1:
            raise ValueError("provider cannot be empty")
        if not self.model or len(self.model.strip()) < 1:
            raise ValueError("model cannot be empty")
        if not self.status or len(self.status.strip()) < 1:
            raise ValueError("status cannot be empty")
        if not self.timestamp or len(self.timestamp.strip()) < 1:
            raise ValueError("timestamp cannot be empty")
        try:
            datetime.fromisoformat(self.timestamp)
        except (ValueError, TypeError):
            raise ValueError("timestamp must be a valid ISO format datetime string")


@dataclass
class CallRecord:
    """In-memory call record for instrumentation logging.

    Used by InstrumentedProvider to capture call metadata before
    emitting as structured JSON log or persisting to DB.
    """

    call_id: str
    timestamp: datetime
    provider: str
    model: str
    prompt_name: str = "unknown"
    prompt_tokens: Optional[int] = None
    response_tokens: Optional[int] = None
    latency_ms: int = 0
    status: str = "success"
    error_message: Optional[str] = None
    application_id: Optional[int] = None
    role_id: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dictionary."""
        return {
            "call_id": self.call_id,
            "timestamp": self.timestamp.isoformat(),
            "provider": self.provider,
            "model": self.model,
            "prompt_name": self.prompt_name,
            "prompt_tokens": self.prompt_tokens,
            "response_tokens": self.response_tokens,
            "latency_ms": self.latency_ms,
            "status": self.status,
            "error_message": self.error_message,
            "application_id": self.application_id,
            "role_id": self.role_id,
        }
