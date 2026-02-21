"""Tests for LLM call instrumentation: InstrumentedProvider, CallRecord, CircuitBreaker, RatePacer."""

import asyncio
import json
from datetime import datetime, timezone
from time import monotonic
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.llm.base import LLMProvider
from app.llm.circuit_breaker import CircuitBreaker, CircuitOpenError
from app.llm.instrumented_provider import (
    DBCallLogger,
    DefaultCallLogger,
    InstrumentedProvider,
)
from app.llm.rate_pacer import RatePacer
from app.llm.types import Message, Role, ToolCall
from app.models.llm_call_log import CallRecord, LLMCallLog


# ============================================================
# Helpers
# ============================================================

def _make_mock_inner(model_name: str = "gemini-2.0-flash") -> AsyncMock:
    """Create a mock LLMProvider with default return values."""
    mock = AsyncMock(spec=LLMProvider)
    mock.get_model_name.return_value = model_name
    mock.generate.return_value = Message(role=Role.ASSISTANT, content="Hello")
    mock.generate_with_tools.return_value = (
        Message(role=Role.ASSISTANT, content="Tool result"),
        [ToolCall(id="tool_1", name="web_search", arguments={"query": "test"})],
    )
    return mock


def _make_provider(
    mock_inner: AsyncMock | None = None,
    mock_logger: AsyncMock | None = None,
    provider_name: str = "gemini",
) -> tuple[InstrumentedProvider, AsyncMock, AsyncMock]:
    """Create InstrumentedProvider with mocks, returning (provider, inner, logger)."""
    inner = mock_inner or _make_mock_inner()
    logger = mock_logger or AsyncMock()
    provider = InstrumentedProvider(inner=inner, logger=logger, provider_name=provider_name)
    return provider, inner, logger


# ============================================================
# InstrumentedProvider — generate()
# ============================================================

class TestInstrumentedProviderGenerate:
    @pytest.mark.asyncio
    async def test_success_logs_record(self):
        provider, inner, logger = _make_provider()
        messages = [Message(role=Role.USER, content="Hi")]

        result = await provider.generate(messages)

        assert result.content == "Hello"
        logger.log.assert_called_once()
        record: CallRecord = logger.log.call_args[0][0]
        assert record.status == "success"
        assert record.latency_ms >= 0
        assert record.call_id is not None
        assert record.error_message is None

    @pytest.mark.asyncio
    async def test_failure_logs_record_and_reraises(self):
        provider, inner, logger = _make_provider()
        inner.generate.side_effect = RuntimeError("API down")

        with pytest.raises(RuntimeError, match="API down"):
            await provider.generate([Message(role=Role.USER, content="Hi")])

        logger.log.assert_called_once()
        record: CallRecord = logger.log.call_args[0][0]
        assert record.status == "error"
        assert record.error_message == "API down"
        assert record.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_record_has_all_required_fields(self):
        provider, inner, logger = _make_provider()
        await provider.generate([Message(role=Role.USER, content="Hi")])

        record: CallRecord = logger.log.call_args[0][0]
        record_dict = record.to_dict()
        required_fields = ["call_id", "timestamp", "provider", "model", "latency_ms", "status"]
        for field_name in required_fields:
            assert field_name in record_dict, f"Missing field: {field_name}"

    @pytest.mark.asyncio
    async def test_provider_field_from_provider_name(self):
        provider, inner, logger = _make_provider(provider_name="gemini")
        await provider.generate([Message(role=Role.USER, content="Hi")])

        record: CallRecord = logger.log.call_args[0][0]
        assert record.provider == "gemini"

    @pytest.mark.asyncio
    async def test_model_field_from_inner_get_model_name(self):
        inner = _make_mock_inner(model_name="gemini-2.0-flash")
        provider, _, logger = _make_provider(mock_inner=inner)
        await provider.generate([Message(role=Role.USER, content="Hi")])

        record: CallRecord = logger.log.call_args[0][0]
        assert record.model == "gemini-2.0-flash"


# ============================================================
# InstrumentedProvider — generate_with_tools()
# ============================================================

class TestInstrumentedProviderGenerateWithTools:
    @pytest.mark.asyncio
    async def test_success_logs_record(self):
        provider, inner, logger = _make_provider()
        messages = [Message(role=Role.USER, content="Search")]

        result = await provider.generate_with_tools(messages, tools=[])

        assert isinstance(result, tuple)
        message, tool_calls = result
        assert message.content == "Tool result"
        assert len(tool_calls) == 1
        logger.log.assert_called_once()
        record: CallRecord = logger.log.call_args[0][0]
        assert record.status == "success"

    @pytest.mark.asyncio
    async def test_failure_logs_and_reraises(self):
        provider, inner, logger = _make_provider()
        inner.generate_with_tools.side_effect = RuntimeError("Tool error")

        with pytest.raises(RuntimeError, match="Tool error"):
            await provider.generate_with_tools([Message(role=Role.USER, content="Hi")], tools=[])

        record: CallRecord = logger.log.call_args[0][0]
        assert record.status == "error"


# ============================================================
# InstrumentedProvider — generate_stream()
# ============================================================

class TestInstrumentedProviderGenerateStream:
    @pytest.mark.asyncio
    async def test_success_logs_after_stream_completes(self):
        provider, inner, logger = _make_provider()

        async def mock_stream(*args, **kwargs):
            yield "Hello "
            yield "world"

        inner.generate_stream = mock_stream

        chunks = []
        async for chunk in provider.generate_stream([Message(role=Role.USER, content="Hi")]):
            chunks.append(chunk)

        assert chunks == ["Hello ", "world"]
        logger.log.assert_called_once()
        record: CallRecord = logger.log.call_args[0][0]
        assert record.status == "success"
        assert record.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_error_during_stream_logs_and_reraises(self):
        provider, inner, logger = _make_provider()

        async def mock_stream_error(*args, **kwargs):
            yield "partial"
            raise RuntimeError("Stream failed")

        inner.generate_stream = mock_stream_error

        chunks = []
        with pytest.raises(RuntimeError, match="Stream failed"):
            async for chunk in provider.generate_stream([Message(role=Role.USER, content="Hi")]):
                chunks.append(chunk)

        assert chunks == ["partial"]
        logger.log.assert_called_once()
        record: CallRecord = logger.log.call_args[0][0]
        assert record.status == "error"
        assert record.error_message == "Stream failed"


# ============================================================
# InstrumentedProvider — passthrough methods
# ============================================================

class TestInstrumentedProviderPassthrough:
    def test_set_system_instruction_delegates(self):
        provider, inner, logger = _make_provider()
        provider.set_system_instruction("You are a helpful assistant")
        inner.set_system_instruction.assert_called_once_with("You are a helpful assistant")

    def test_get_model_name_delegates(self):
        inner = _make_mock_inner(model_name="gemini-2.0-flash")
        provider, _, _ = _make_provider(mock_inner=inner)
        assert provider.get_model_name() == "gemini-2.0-flash"


# ============================================================
# Factory integration
# ============================================================

class TestFactoryIntegration:
    def test_get_llm_provider_returns_instrumented(self):
        from app.llm import get_llm_provider, reset_provider
        from app.llm.config import LLMConfig

        reset_provider()
        try:
            # Use a fake config that will create a GeminiProvider
            # This will fail without a real API key, so we mock _create_provider
            with patch("app.llm._create_provider") as mock_create:
                mock_inner = _make_mock_inner()
                mock_create.return_value = mock_inner

                config = LLMConfig(provider="gemini", api_key="fake-key", model="gemini-2.0-flash")
                provider = get_llm_provider(config)

                assert isinstance(provider, InstrumentedProvider)
        finally:
            reset_provider()

    def test_reset_provider_clears_singleton(self):
        from app.llm import get_llm_provider, reset_provider

        reset_provider()
        try:
            with patch("app.llm._create_provider") as mock_create:
                mock_inner = _make_mock_inner()
                mock_create.return_value = mock_inner
                config = MagicMock()
                config.provider = "gemini"

                provider1 = get_llm_provider(config)
                reset_provider()
                provider2 = get_llm_provider(config)

                assert provider1 is not provider2
                assert isinstance(provider2, InstrumentedProvider)
        finally:
            reset_provider()


# ============================================================
# CallRecord model
# ============================================================

class TestCallRecord:
    def test_instantiation(self):
        record = CallRecord(
            call_id="test-123",
            timestamp=datetime.now(timezone.utc),
            provider="gemini",
            model="gemini-2.0-flash",
        )
        assert record.call_id == "test-123"
        assert record.status == "success"
        assert record.prompt_name == "unknown"

    def test_to_dict_serialization(self):
        ts = datetime(2026, 2, 7, 12, 0, 0, tzinfo=timezone.utc)
        record = CallRecord(
            call_id="abc-123",
            timestamp=ts,
            provider="gemini",
            model="gemini-2.0-flash",
            latency_ms=500,
            status="success",
        )
        d = record.to_dict()
        assert d["call_id"] == "abc-123"
        assert d["timestamp"] == "2026-02-07T12:00:00+00:00"
        assert d["provider"] == "gemini"
        assert d["model"] == "gemini-2.0-flash"
        assert d["latency_ms"] == 500
        assert d["status"] == "success"
        assert d["prompt_tokens"] is None
        assert d["error_message"] is None

    def test_to_dict_is_json_serializable(self):
        record = CallRecord(
            call_id="xyz",
            timestamp=datetime.now(timezone.utc),
            provider="gemini",
            model="test-model",
        )
        json_str = json.dumps(record.to_dict())
        parsed = json.loads(json_str)
        assert parsed["call_id"] == "xyz"


# ============================================================
# LLMCallLog SQLModel
# ============================================================

class TestLLMCallLog:
    def test_table_instantiation(self):
        log = LLMCallLog(
            call_id="test-id",
            timestamp="2026-02-07T12:00:00+00:00",
            provider="gemini",
            model="gemini-2.0-flash",
            status="success",
            latency_ms=100,
        )
        assert log.call_id == "test-id"
        assert log.provider == "gemini"
        assert log.status == "success"

    def test_validation_empty_call_id(self):
        with pytest.raises(ValueError, match="call_id cannot be empty"):
            LLMCallLog(
                call_id="",
                timestamp="2026-02-07T12:00:00+00:00",
                provider="gemini",
                model="gemini-2.0-flash",
                status="success",
            )

    def test_validation_empty_provider(self):
        with pytest.raises(ValueError, match="provider cannot be empty"):
            LLMCallLog(
                call_id="test-id",
                timestamp="2026-02-07T12:00:00+00:00",
                provider="",
                model="gemini-2.0-flash",
                status="success",
            )

    def test_table_creation(self):
        """Verify LLMCallLog has table=True metadata."""
        assert hasattr(LLMCallLog, "__tablename__")
        assert LLMCallLog.__tablename__ == "llm_call_log"


# ============================================================
# DefaultCallLogger
# ============================================================

class TestDefaultCallLogger:
    @pytest.mark.asyncio
    async def test_success_logs_at_info(self):
        logger_instance = DefaultCallLogger()
        record = CallRecord(
            call_id="test",
            timestamp=datetime.now(timezone.utc),
            provider="gemini",
            model="test",
            status="success",
        )
        with patch("app.llm.instrumented_provider.logger") as mock_logger:
            await logger_instance.log(record)
            mock_logger.info.assert_called_once()
            logged_json = json.loads(mock_logger.info.call_args[0][0])
            assert logged_json["status"] == "success"

    @pytest.mark.asyncio
    async def test_error_logs_at_warning(self):
        logger_instance = DefaultCallLogger()
        record = CallRecord(
            call_id="test",
            timestamp=datetime.now(timezone.utc),
            provider="gemini",
            model="test",
            status="error",
            error_message="boom",
        )
        with patch("app.llm.instrumented_provider.logger") as mock_logger:
            await logger_instance.log(record)
            mock_logger.warning.assert_called_once()
            logged_json = json.loads(mock_logger.warning.call_args[0][0])
            assert logged_json["status"] == "error"
            assert logged_json["error_message"] == "boom"


# ============================================================
# DBCallLogger
# ============================================================

class TestDBCallLogger:
    @pytest.mark.asyncio
    async def test_successful_persist(self):
        record = CallRecord(
            call_id="db-test",
            timestamp=datetime.now(timezone.utc),
            provider="gemini",
            model="test",
            status="success",
        )

        mock_session = AsyncMock()
        mock_session.add = MagicMock()  # AsyncSession.add() is synchronous
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cm.__aexit__ = AsyncMock(return_value=False)

        mock_session_maker = MagicMock(return_value=mock_cm)
        db_logger = DBCallLogger(session_maker=mock_session_maker)
        await db_logger.log(record)
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_persist_failure_caught_and_logged(self):
        record = CallRecord(
            call_id="db-fail",
            timestamp=datetime.now(timezone.utc),
            provider="gemini",
            model="test",
            status="success",
        )

        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(side_effect=RuntimeError("DB connection failed"))
        mock_cm.__aexit__ = AsyncMock(return_value=False)

        mock_session_maker = MagicMock(return_value=mock_cm)
        db_logger = DBCallLogger(session_maker=mock_session_maker)
        with patch("app.llm.instrumented_provider.logger") as mock_logger:
            # Should NOT raise
            await db_logger.log(record)
            mock_logger.error.assert_called_once()


# ============================================================
# CircuitBreaker
# ============================================================

class TestCircuitBreaker:
    def test_starts_closed(self):
        cb = CircuitBreaker()
        assert cb.can_proceed() is True

    def test_n_minus_1_failures_keeps_closed(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.can_proceed() is True

    def test_n_failures_trips_to_open(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.can_proceed() is False

    def test_record_success_resets_and_closes(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.can_proceed() is False
        cb.record_success()
        assert cb.can_proceed() is True

    def test_half_open_after_reset_timeout(self):
        cb = CircuitBreaker(failure_threshold=1, reset_timeout=0.01)
        cb.record_failure()
        assert cb.can_proceed() is False

        import time
        time.sleep(0.02)
        assert cb.can_proceed() is True
        # State should now be half-open

    def test_success_in_half_open_closes_circuit(self):
        cb = CircuitBreaker(failure_threshold=1, reset_timeout=0.01)
        cb.record_failure()

        import time
        time.sleep(0.02)
        assert cb.can_proceed() is True  # half-open
        cb.record_success()
        assert cb.can_proceed() is True  # closed

    def test_failure_in_half_open_reopens_circuit(self):
        cb = CircuitBreaker(failure_threshold=1, reset_timeout=0.01)
        cb.record_failure()

        import time
        time.sleep(0.02)
        assert cb.can_proceed() is True  # half-open
        cb.record_failure()
        assert cb.can_proceed() is False  # re-opened

    def test_circuit_open_error(self):
        err = CircuitOpenError("Circuit is open")
        assert str(err) == "Circuit is open"


# ============================================================
# RatePacer
# ============================================================

class TestRatePacer:
    @pytest.mark.asyncio
    async def test_first_call_no_delay(self):
        pacer = RatePacer(min_interval_seconds=1.0)
        start = monotonic()
        await pacer.pace()
        elapsed = monotonic() - start
        assert elapsed < 0.1  # Should be nearly instant

    @pytest.mark.asyncio
    async def test_second_call_within_interval_is_delayed(self):
        pacer = RatePacer(min_interval_seconds=0.1)
        await pacer.pace()

        start = monotonic()
        await pacer.pace()
        elapsed = monotonic() - start
        assert elapsed >= 0.05  # Should have waited ~0.1s

    @pytest.mark.asyncio
    async def test_second_call_after_interval_no_delay(self):
        pacer = RatePacer(min_interval_seconds=0.05)
        await pacer.pace()
        await asyncio.sleep(0.06)

        start = monotonic()
        await pacer.pace()
        elapsed = monotonic() - start
        assert elapsed < 0.05  # Should be nearly instant

    @pytest.mark.asyncio
    async def test_concurrent_calls_serialized(self):
        pacer = RatePacer(min_interval_seconds=0.05)
        call_times = []

        async def paced_call():
            await pacer.pace()
            call_times.append(monotonic())

        # Launch 3 concurrent calls
        await asyncio.gather(paced_call(), paced_call(), paced_call())

        # All 3 should have completed
        assert len(call_times) == 3

        # Calls should be spaced out
        call_times.sort()
        for i in range(1, len(call_times)):
            gap = call_times[i] - call_times[i - 1]
            assert gap >= 0.04  # Allow small timing tolerance


# ============================================================
# LLM_MODEL_GEN Provider Factory Tests
# ============================================================


class TestGetLLMProviderForGeneration:
    """Test get_llm_provider_for_generation respects LLM_MODEL_GEN."""

    def test_returns_default_when_no_override(self):
        """When LLM_MODEL_GEN is empty, returns the default singleton."""
        from app.llm import get_llm_provider_for_generation, reset_provider

        reset_provider()
        with patch("app.config.settings") as mock_settings:
            mock_settings.llm_model_gen = ""
            mock_settings.llm_provider = "gemini"
            mock_settings.llm_api_key = "test-key"
            mock_settings.llm_model = "gemini-2.0-flash-exp"

            with patch("app.llm._create_provider") as mock_create:
                mock_inner = _make_mock_inner("gemini-2.0-flash-exp")
                mock_create.return_value = mock_inner

                p1 = get_llm_provider_for_generation()
                p2 = get_llm_provider_for_generation()
                # Should be the same singleton instance
                assert p1 is p2

        reset_provider()

    def test_creates_fresh_provider_with_override(self):
        """When LLM_MODEL_GEN is set, creates a non-cached provider."""
        from app.llm import get_llm_provider_for_generation, reset_provider

        reset_provider()
        with patch("app.config.settings") as mock_settings:
            mock_settings.llm_model_gen = "gemini-2.5-pro"
            mock_settings.llm_provider = "gemini"
            mock_settings.llm_api_key = "test-key"
            mock_settings.llm_model = "gemini-2.0-flash-exp"

            with patch("app.llm._create_provider") as mock_create:
                mock_inner = _make_mock_inner("gemini-2.5-pro")
                mock_create.return_value = mock_inner

                provider = get_llm_provider_for_generation()

                # Verify _create_provider was called with the override model
                call_config = mock_create.call_args[0][0]
                assert call_config.model == "gemini-2.5-pro"
                assert isinstance(provider, InstrumentedProvider)

        reset_provider()

    def test_override_provider_not_cached_as_singleton(self):
        """Override provider must NOT pollute the singleton."""
        from app.llm import get_llm_provider, get_llm_provider_for_generation, reset_provider

        reset_provider()
        with patch("app.config.settings") as mock_settings:
            mock_settings.llm_model_gen = "gemini-2.5-pro"
            mock_settings.llm_provider = "gemini"
            mock_settings.llm_api_key = "test-key"
            mock_settings.llm_model = "gemini-2.0-flash-exp"

            with patch("app.llm._create_provider") as mock_create:
                mock_inner_default = _make_mock_inner("gemini-2.0-flash-exp")
                mock_inner_gen = _make_mock_inner("gemini-2.5-pro")
                mock_create.side_effect = [mock_inner_default, mock_inner_gen]

                default = get_llm_provider()
                gen = get_llm_provider_for_generation()

                # They should be different instances
                assert default is not gen

        reset_provider()
