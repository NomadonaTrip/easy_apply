"""Tests for research service, SSE manager, and research API endpoints."""

import asyncio
import json

import pytest

from app.models.research import (
    ResearchStatus,
    ResearchCategory,
    ResearchSourceResult,
    ResearchResult,
    ResearchProgressEvent,
    ResearchCompleteEvent,
    ResearchErrorEvent,
)
from app.services.sse_manager import SSEManager
from app.services.research_service import ResearchService


# ============================================================================
# Research Models Tests (Task 4)
# ============================================================================


class TestResearchModels:
    """Test research model schemas and enums."""

    def test_research_status_enum_values(self):
        assert ResearchStatus.PENDING == "pending"
        assert ResearchStatus.RUNNING == "running"
        assert ResearchStatus.COMPLETE == "complete"
        assert ResearchStatus.FAILED == "failed"

    def test_research_category_enum_values(self):
        assert ResearchCategory.STRATEGIC_INITIATIVES == "strategic_initiatives"
        assert ResearchCategory.COMPETITIVE_LANDSCAPE == "competitive_landscape"
        assert ResearchCategory.NEWS_MOMENTUM == "news_momentum"
        assert ResearchCategory.INDUSTRY_CONTEXT == "industry_context"
        assert ResearchCategory.CULTURE_VALUES == "culture_values"
        assert ResearchCategory.LEADERSHIP_DIRECTION == "leadership_direction"

    def test_research_source_result_found(self):
        result = ResearchSourceResult(found=True, content="Some content")
        assert result.found is True
        assert result.content == "Some content"
        assert result.reason is None

    def test_research_source_result_not_found(self):
        result = ResearchSourceResult(found=False, reason="Source unavailable")
        assert result.found is False
        assert result.content is None
        assert result.reason == "Source unavailable"

    def test_research_progress_event(self):
        event = ResearchProgressEvent(source="strategic_initiatives", message="Investigating...")
        assert event.type == "progress"
        assert event.source == "strategic_initiatives"
        assert event.status == "searching"
        assert event.message == "Investigating..."

    def test_research_progress_event_custom_status(self):
        event = ResearchProgressEvent(source="competitive_landscape", status="analyzing", message="Deep dive...")
        assert event.status == "analyzing"

    def test_research_complete_event(self):
        result = ResearchSourceResult(found=True, content="data")
        event = ResearchCompleteEvent(research_data={"strategic_initiatives": result})
        assert event.type == "complete"
        assert "strategic_initiatives" in event.research_data

    def test_research_error_event(self):
        event = ResearchErrorEvent(message="Something failed")
        assert event.type == "error"
        assert event.message == "Something failed"

    def test_research_result_with_gaps(self):
        result = ResearchResult(
            strategic_initiatives=ResearchSourceResult(found=True, content="data"),
            industry_context=ResearchSourceResult(found=False, reason="Limited public information"),
            gaps=["industry_context"],
            completed_at="2026-02-08T00:00:00Z",
        )
        assert result.strategic_initiatives.found is True
        assert result.industry_context.found is False
        assert "industry_context" in result.gaps
        assert result.completed_at is not None

    def test_research_result_default_gaps_empty(self):
        result = ResearchResult()
        assert result.gaps == []
        assert result.completed_at is None


# ============================================================================
# SSE Manager Tests (Task 2)
# ============================================================================


class TestSSEManager:
    """Test SSEManager event streaming."""

    @pytest.mark.asyncio
    async def test_create_stream_and_receive_event(self):
        manager = SSEManager()

        async def producer():
            await asyncio.sleep(0.05)
            await manager.send_event(1, "progress", {"source": "test", "message": "Testing..."})
            await asyncio.sleep(0.05)
            await manager.send_event(1, "complete", {"summary": "Done"})

        asyncio.create_task(producer())

        events = []
        async for event_str in manager.create_stream(1):
            events.append(event_str)

        assert len(events) == 2
        first = json.loads(events[0].replace("data: ", "").strip())
        assert first["type"] == "progress"
        assert first["source"] == "test"

        second = json.loads(events[1].replace("data: ", "").strip())
        assert second["type"] == "complete"

    @pytest.mark.asyncio
    async def test_stream_closes_on_complete_event(self):
        manager = SSEManager()

        async def producer():
            await asyncio.sleep(0.05)
            await manager.send_event(1, "complete", {"summary": "Done"})

        asyncio.create_task(producer())

        events = []
        async for event_str in manager.create_stream(1):
            events.append(event_str)

        assert len(events) == 1
        assert not manager.is_active(1)

    @pytest.mark.asyncio
    async def test_stream_closes_on_error_event(self):
        manager = SSEManager()

        async def producer():
            await asyncio.sleep(0.05)
            await manager.send_event(1, "error", {"message": "Failed"})

        asyncio.create_task(producer())

        events = []
        async for event_str in manager.create_stream(1):
            events.append(event_str)

        assert len(events) == 1
        data = json.loads(events[0].replace("data: ", "").strip())
        assert data["type"] == "error"
        assert not manager.is_active(1)

    @pytest.mark.asyncio
    async def test_send_event_to_nonexistent_stream(self):
        manager = SSEManager()
        # Should not raise
        await manager.send_event(999, "progress", {"message": "No one listening"})

    @pytest.mark.asyncio
    async def test_is_active_returns_false_for_unknown(self):
        manager = SSEManager()
        assert manager.is_active(999) is False

    @pytest.mark.asyncio
    async def test_close_stream(self):
        manager = SSEManager()
        manager._streams[1] = asyncio.Queue()
        manager._active[1] = True

        manager.close_stream(1)
        assert manager._active[1] is False

    @pytest.mark.asyncio
    async def test_cleanup_removes_resources(self):
        manager = SSEManager()
        manager._streams[1] = asyncio.Queue()
        manager._active[1] = True

        manager._cleanup(1)
        assert 1 not in manager._streams
        assert 1 not in manager._active

    @pytest.mark.asyncio
    async def test_create_stream_reuses_existing_queue(self):
        """Verify create_stream reuses an existing queue instead of replacing it."""
        manager = SSEManager()
        # Pre-create a queue and put an event on it
        queue = asyncio.Queue()
        manager._streams[1] = queue
        await queue.put({"type": "complete", "summary": "Pre-loaded"})

        # create_stream should reuse the existing queue (with the pre-loaded event)
        events = []
        async for event_str in manager.create_stream(1):
            events.append(event_str)

        assert len(events) == 1
        data = json.loads(events[0].replace("data: ", "").strip())
        assert data["summary"] == "Pre-loaded"

    @pytest.mark.asyncio
    async def test_multiple_progress_events_before_complete(self):
        manager = SSEManager()

        async def producer():
            await asyncio.sleep(0.05)
            for i in range(3):
                await manager.send_event(1, "progress", {"source": f"src_{i}", "message": f"Step {i}"})
                await asyncio.sleep(0.02)
            await manager.send_event(1, "complete", {"summary": "All done"})

        asyncio.create_task(producer())

        events = []
        async for event_str in manager.create_stream(1):
            events.append(event_str)

        assert len(events) == 4  # 3 progress + 1 complete


# ============================================================================
# Research Service Tests (Task 1)
# ============================================================================


class TestResearchService:
    """Test ResearchService business logic."""

    def test_get_status_returns_none_for_unknown(self):
        service = ResearchService()
        assert service.get_status(999) is None

    def test_is_running_returns_false_for_unknown(self):
        service = ResearchService()
        assert service.is_running(999) is False

    def test_is_running_returns_true_when_running(self):
        service = ResearchService()
        service._research_state[1] = ResearchStatus.RUNNING
        assert service.is_running(1) is True

    def test_is_running_returns_false_when_complete(self):
        service = ResearchService()
        service._research_state[1] = ResearchStatus.COMPLETE
        assert service.is_running(1) is False

    @pytest.mark.asyncio
    async def test_cancel_research_when_running(self, monkeypatch):
        """Test cancel_research stops running research and sends error event."""
        service = ResearchService()
        manager = SSEManager()

        import app.services.research_service as rs_module
        monkeypatch.setattr(rs_module, "sse_manager", manager)

        service._research_state[1] = ResearchStatus.RUNNING
        queue = asyncio.Queue()
        manager._streams[1] = queue
        manager._active[1] = True

        result = await service.cancel_research(1)

        assert result is True
        assert service.get_status(1) is None  # State cleaned up
        assert not manager.is_active(1)

        # Verify error event content was queued correctly (M3 fix)
        event = queue.get_nowait()
        assert event["type"] == "error"
        assert event["message"] == "Research cancelled"
        assert event["recoverable"] is False

    @pytest.mark.asyncio
    async def test_cancel_research_when_not_running(self):
        service = ResearchService()
        result = await service.cancel_research(999)
        assert result is False

    @pytest.mark.asyncio
    async def test_start_research_sends_progress_and_complete_events(self, monkeypatch):
        """Integration test: verify start_research produces correct SSE event sequence."""
        service = ResearchService()
        manager = SSEManager()

        import app.services.research_service as rs_module
        monkeypatch.setattr(rs_module, "sse_manager", manager)

        async def mock_update(*args, **kwargs):
            return None

        monkeypatch.setattr(service, "_save_research_results", mock_update)

        events = []

        async def consumer():
            async for event_str in manager.create_stream(1):
                events.append(json.loads(event_str.replace("data: ", "").strip()))

        consumer_task = asyncio.create_task(consumer())

        await asyncio.sleep(0.05)  # Let consumer start
        await service.start_research(1, 1, "TestCorp", "Software engineer role")
        await asyncio.sleep(0.1)  # Let consumer finish

        # 6 progress events + 1 complete event
        progress_events = [e for e in events if e["type"] == "progress"]
        complete_events = [e for e in events if e["type"] == "complete"]

        assert len(progress_events) == 6
        assert len(complete_events) == 1

        # Verify progress event structure per architecture spec
        for pe in progress_events:
            assert "source" in pe
            assert "status" in pe
            assert "message" in pe
            assert pe["status"] == "searching"

        # Verify complete event has research_data with 6 categories
        assert "research_data" in complete_events[0]
        assert len(complete_events[0]["research_data"]) == 6

        # Verify state is cleaned up
        assert service.get_status(1) is None

        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_start_research_handles_source_exception(self, monkeypatch):
        """Test that an exception during research sends an error event."""
        service = ResearchService()
        manager = SSEManager()

        import app.services.research_service as rs_module
        monkeypatch.setattr(rs_module, "sse_manager", manager)

        async def failing_research(source, company, posting):
            raise RuntimeError("LLM provider unavailable")

        monkeypatch.setattr(service, "_research_category", failing_research)

        events = []

        async def consumer():
            async for event_str in manager.create_stream(1):
                events.append(json.loads(event_str.replace("data: ", "").strip()))

        consumer_task = asyncio.create_task(consumer())
        await asyncio.sleep(0.05)

        await service.start_research(1, 1, "TestCorp", "Engineer role")
        await asyncio.sleep(0.1)

        error_events = [e for e in events if e["type"] == "error"]
        assert len(error_events) == 1
        assert "LLM provider unavailable" in error_events[0]["message"]
        assert error_events[0]["recoverable"] is False

        # State cleaned up
        assert service.get_status(1) is None

        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass


# ============================================================================
# Research API Endpoint Tests (Task 3 & Task 6)
# ============================================================================


def _auth_helper(client):
    """Register, login, create role, and create application. Returns (role_id, app_id, headers)."""
    client.post("/api/v1/auth/register", json={
        "username": "testuser",
        "password": "testpass123",
    })
    client.post("/api/v1/auth/login", json={
        "username": "testuser",
        "password": "testpass123",
    })
    role_resp = client.post("/api/v1/roles", json={"name": "Test Role"})
    role_id = role_resp.json()["id"]
    headers = {"X-Role-Id": str(role_id)}

    app_resp = client.post(
        "/api/v1/applications",
        json={
            "company_name": "Test Corp",
            "job_posting": "We are looking for a software engineer with 5 years of experience.",
        },
        headers=headers,
    )
    app_id = app_resp.json()["id"]

    return role_id, app_id, headers


class TestResearchEndpoints:
    """Test research API endpoints."""

    @pytest.fixture(autouse=True)
    def _cleanup_research_state(self):
        """Clean up global singleton state after each test."""
        from app.services.research_service import research_service
        yield
        research_service._research_state.clear()

    def test_start_research_returns_started(self, client):
        _role_id, app_id, headers = _auth_helper(client)

        response = client.post(
            f"/api/v1/applications/{app_id}/research",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
        assert data["application_id"] == app_id

    def test_start_research_rejects_nonexistent_application(self, client):
        client.post("/api/v1/auth/register", json={
            "username": "testuser",
            "password": "testpass123",
        })
        client.post("/api/v1/auth/login", json={
            "username": "testuser",
            "password": "testpass123",
        })
        role_resp = client.post("/api/v1/roles", json={"name": "Test Role"})
        role_id = role_resp.json()["id"]
        headers = {"X-Role-Id": str(role_id)}

        response = client.post(
            "/api/v1/applications/9999/research",
            headers=headers,
        )
        assert response.status_code == 404

    def test_start_research_requires_auth(self, client):
        response = client.post("/api/v1/applications/1/research")
        assert response.status_code == 401

    def test_start_research_requires_role_header(self, client):
        client.post("/api/v1/auth/register", json={
            "username": "testuser",
            "password": "testpass123",
        })
        client.post("/api/v1/auth/login", json={
            "username": "testuser",
            "password": "testpass123",
        })

        response = client.post("/api/v1/applications/1/research")
        assert response.status_code == 400

    def test_start_research_rejects_concurrent(self, client):
        """Test that concurrent research requests return 409."""
        from app.services.research_service import research_service
        _role_id, app_id, headers = _auth_helper(client)

        # Simulate research already running
        research_service._research_state[app_id] = ResearchStatus.RUNNING

        response = client.post(
            f"/api/v1/applications/{app_id}/research",
            headers=headers,
        )
        assert response.status_code == 409
        assert "already in progress" in response.json()["detail"]

    def test_research_status_not_started(self, client):
        _role_id, app_id, headers = _auth_helper(client)

        response = client.get(
            f"/api/v1/applications/{app_id}/research/status",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "not_started"
        assert data["has_research_data"] is False

    def test_research_status_requires_auth(self, client):
        response = client.get("/api/v1/applications/1/research/status")
        assert response.status_code == 401

    def test_research_status_nonexistent_application(self, client):
        client.post("/api/v1/auth/register", json={
            "username": "testuser",
            "password": "testpass123",
        })
        client.post("/api/v1/auth/login", json={
            "username": "testuser",
            "password": "testpass123",
        })
        role_resp = client.post("/api/v1/roles", json={"name": "Test Role"})
        role_id = role_resp.json()["id"]
        headers = {"X-Role-Id": str(role_id)}

        response = client.get(
            "/api/v1/applications/9999/research/status",
            headers=headers,
        )
        assert response.status_code == 404

    def test_stream_requires_valid_application(self, client):
        """Verify the stream endpoint validates application access.

        Full SSE streaming behavior is tested in SSEManager unit tests.
        TestClient cannot easily handle concurrent producers for SSE streams,
        so integration streaming is validated via SSEManager tests.
        """
        _role_id, app_id, headers = _auth_helper(client)

        # Verify 404 for nonexistent application (auth is valid)
        response = client.get(
            "/api/v1/applications/9999/research/stream",
            headers=headers,
        )
        assert response.status_code == 404

    def test_stream_requires_auth(self, client):
        response = client.get("/api/v1/applications/1/research/stream")
        assert response.status_code == 401

    def test_stream_nonexistent_application(self, client):
        client.post("/api/v1/auth/register", json={
            "username": "testuser",
            "password": "testpass123",
        })
        client.post("/api/v1/auth/login", json={
            "username": "testuser",
            "password": "testpass123",
        })
        role_resp = client.post("/api/v1/roles", json={"name": "Test Role"})
        role_id = role_resp.json()["id"]
        headers = {"X-Role-Id": str(role_id)}

        response = client.get(
            "/api/v1/applications/9999/research/stream",
            headers=headers,
        )
        assert response.status_code == 404

    def test_role_isolation_prevents_cross_role_access(self, client):
        """Test that user A cannot research user B's application."""
        # Create user A with role and application
        client.post("/api/v1/auth/register", json={
            "username": "userA",
            "password": "testpass123",
        })
        client.post("/api/v1/auth/login", json={
            "username": "userA",
            "password": "testpass123",
        })
        role_a_resp = client.post("/api/v1/roles", json={"name": "Role A"})
        role_a_id = role_a_resp.json()["id"]
        app_resp = client.post(
            "/api/v1/applications",
            json={
                "company_name": "Corp A",
                "job_posting": "Software engineer role requiring expertise.",
            },
            headers={"X-Role-Id": str(role_a_id)},
        )
        app_id = app_resp.json()["id"]

        # Logout and create user B
        client.post("/api/v1/auth/logout")
        client.post("/api/v1/auth/register", json={
            "username": "userB",
            "password": "testpass123",
        })
        client.post("/api/v1/auth/login", json={
            "username": "userB",
            "password": "testpass123",
        })
        role_b_resp = client.post("/api/v1/roles", json={"name": "Role B"})
        role_b_id = role_b_resp.json()["id"]

        # User B tries to research user A's application
        response = client.post(
            f"/api/v1/applications/{app_id}/research",
            headers={"X-Role-Id": str(role_b_id)},
        )
        assert response.status_code == 404  # Application not found for this role

    def test_start_research_sets_status_to_researching(self, client):
        """Test that starting research updates application status to RESEARCHING (H1 fix)."""
        _role_id, app_id, headers = _auth_helper(client)

        # Verify initial status is 'created'
        app_resp = client.get(f"/api/v1/applications/{app_id}", headers=headers)
        assert app_resp.json()["status"] == "created"

        # Start research
        response = client.post(
            f"/api/v1/applications/{app_id}/research",
            headers=headers,
        )
        assert response.status_code == 200

        # Verify status updated to 'researching'
        app_resp = client.get(f"/api/v1/applications/{app_id}", headers=headers)
        assert app_resp.json()["status"] == "researching"

    def test_start_research_rejects_missing_job_data(self, client, monkeypatch):
        """Test 400 when application lacks company_name or job_posting (M2 fix)."""
        from types import SimpleNamespace
        _role_id, app_id, headers = _auth_helper(client)

        # Mock application_service to return an application with missing job_posting
        mock_app = SimpleNamespace(
            id=app_id, company_name="Corp", job_posting=None, research_data=None,
        )

        async def mock_get_application(id, role_id):
            return mock_app

        monkeypatch.setattr(
            "app.services.application_service.get_application", mock_get_application,
        )

        response = client.post(
            f"/api/v1/applications/{app_id}/research",
            headers=headers,
        )
        assert response.status_code == 400
        assert "company name and job posting" in response.json()["detail"]
