"""Test SSE endpoint for validating streaming behavior."""

import asyncio
import json

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/test", tags=["test"])


@router.get("/sse")
async def test_sse(
    delay: int = Query(default=1000, ge=100, le=10000, description="Delay between events in milliseconds"),
    error_at: int = Query(default=0, ge=0, le=5, description="Inject recoverable error at event N (0 = no error)"),
    fatal_error_at: int = Query(default=0, ge=0, le=5, description="Inject non-recoverable error at event N (0 = no error)"),
):
    """Test SSE endpoint for validating streaming behavior."""

    async def event_generator():
        try:
            sources = [
                ("company_profile", "searching", "Searching company profile..."),
                ("culture_values", "analyzing", "Analyzing culture and values..."),
                ("glassdoor", "searching", "Checking Glassdoor reviews..."),
                ("recent_news", "searching", "Searching recent news..."),
                ("leadership", "analyzing", "Analyzing leadership team..."),
            ]

            for i, (source, status, message) in enumerate(sources, 1):
                # Inject non-recoverable (fatal) error if requested (takes precedence)
                if fatal_error_at > 0 and i == fatal_error_at:
                    event = {
                        "type": "error",
                        "source": source,
                        "message": f"Simulated fatal error at event {i}",
                        "recoverable": False,
                    }
                    yield f"data: {json.dumps(event)}\n\n"
                    return  # End the stream

                # Inject recoverable error if requested
                if error_at > 0 and i == error_at:
                    event = {
                        "type": "error",
                        "source": source,
                        "message": f"Simulated recoverable error at event {i}",
                        "recoverable": True,
                    }
                    yield f"data: {json.dumps(event)}\n\n"
                    continue

                event = {
                    "type": "progress",
                    "source": source,
                    "status": status,
                    "message": message,
                }
                yield f"data: {json.dumps(event)}\n\n"
                await asyncio.sleep(delay / 1000)

            # Final complete event
            complete_event = {
                "type": "complete",
                "summary": f"{len(sources)}/{len(sources)} sources processed",
            }
            yield f"data: {json.dumps(complete_event)}\n\n"

        except asyncio.CancelledError:
            # Client disconnected - clean exit
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
