"""Instrumented LLM provider with structured logging and optional DB persistence."""

import json
import logging
from datetime import datetime, timezone
from time import monotonic
from typing import AsyncIterator, Protocol
from uuid import uuid4

from .base import LLMProvider, Tool
from .types import GenerationConfig, Message, ToolCall

from app.models.llm_call_log import CallRecord

logger = logging.getLogger("app.llm.instrumented")


class CallLogger(Protocol):
    """Protocol for call record loggers."""

    async def log(self, record: CallRecord) -> None:
        """Log a call record."""
        ...


class DefaultCallLogger:
    """Emit call records as structured JSON to Python logger.

    Success records are logged at INFO level.
    Error records are logged at WARNING level.
    """

    async def log(self, record: CallRecord) -> None:
        record_dict = record.to_dict()
        json_str = json.dumps(record_dict)
        if record.status == "error":
            logger.warning(json_str)
        else:
            logger.info(json_str)


class DBCallLogger:
    """Persist call records to database via LLMCallLog table.

    Fire-and-forget: DB failures are caught and logged, never propagated.
    """

    def __init__(self, session_maker=None):
        self._session_maker = session_maker

    async def log(self, record: CallRecord) -> None:
        try:
            from app.models.llm_call_log import LLMCallLog

            session_maker = self._session_maker
            if session_maker is None:
                from app.database import async_session_maker
                session_maker = async_session_maker

            async with session_maker() as session:
                db_record = LLMCallLog(
                    call_id=record.call_id,
                    timestamp=record.timestamp.isoformat(),
                    provider=record.provider,
                    model=record.model,
                    prompt_name=record.prompt_name,
                    prompt_tokens=record.prompt_tokens,
                    response_tokens=record.response_tokens,
                    latency_ms=record.latency_ms,
                    status=record.status,
                    error_message=record.error_message,
                    application_id=record.application_id,
                    role_id=record.role_id,
                )
                session.add(db_record)
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to persist LLM call record to DB: {e}")


class InstrumentedProvider(LLMProvider):
    """Decorator that wraps an LLMProvider with instrumentation.

    Captures timing, status, and error information for every LLM call,
    emitting structured log records via a CallLogger.
    """

    def __init__(
        self,
        inner: LLMProvider,
        logger: CallLogger,
        provider_name: str = "unknown",
    ):
        super().__init__()
        self._inner = inner
        self._logger = logger
        self._provider_name = provider_name

    def _create_record(self) -> CallRecord:
        """Create a new CallRecord with common fields populated."""
        return CallRecord(
            call_id=str(uuid4()),
            timestamp=datetime.now(timezone.utc),
            provider=self._provider_name,
            model=self._inner.get_model_name(),
            prompt_name="unknown",
        )

    def _apply_config_metadata(
        self, record: CallRecord, config: GenerationConfig | None
    ) -> None:
        """Extract observability metadata from config into the call record."""
        if config and config.prompt_name:
            record.prompt_name = config.prompt_name

    async def generate(
        self,
        messages: list[Message],
        config: GenerationConfig | None = None,
    ) -> Message:
        """Generate with instrumentation."""
        record = self._create_record()
        self._apply_config_metadata(record, config)
        start = monotonic()
        try:
            result = await self._inner.generate(messages, config)
            record.status = "success"
            return result
        except Exception as e:
            record.status = "error"
            record.error_message = str(e)
            raise
        finally:
            record.latency_ms = int((monotonic() - start) * 1000)
            await self._logger.log(record)

    async def generate_stream(
        self,
        messages: list[Message],
        config: GenerationConfig | None = None,
    ) -> AsyncIterator[str]:
        """Generate stream with instrumentation."""
        record = self._create_record()
        self._apply_config_metadata(record, config)
        start = monotonic()
        try:
            async for chunk in self._inner.generate_stream(messages, config):
                yield chunk
            record.status = "success"
        except Exception as e:
            record.status = "error"
            record.error_message = str(e)
            raise
        finally:
            record.latency_ms = int((monotonic() - start) * 1000)
            await self._logger.log(record)

    async def generate_with_tools(
        self,
        messages: list[Message],
        tools: list[Tool],
        config: GenerationConfig | None = None,
    ) -> tuple[Message, list[ToolCall]]:
        """Generate with tools with instrumentation."""
        record = self._create_record()
        self._apply_config_metadata(record, config)
        start = monotonic()
        try:
            result = await self._inner.generate_with_tools(messages, tools, config)
            record.status = "success"
            return result
        except Exception as e:
            record.status = "error"
            record.error_message = str(e)
            raise
        finally:
            record.latency_ms = int((monotonic() - start) * 1000)
            await self._logger.log(record)

    def set_system_instruction(self, instruction: str) -> None:
        """Passthrough to inner provider."""
        self._inner.set_system_instruction(instruction)

    def get_model_name(self) -> str:
        """Passthrough to inner provider."""
        return self._inner.get_model_name()
