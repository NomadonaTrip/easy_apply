from fastapi import APIRouter, Depends
from pydantic import BaseModel, HttpUrl

from app.api.deps import get_current_user
from app.services.scrape_service import scrape_job_posting

router = APIRouter(prefix="/scrape", tags=["scrape"])


class ScrapeRequest(BaseModel):
    url: HttpUrl


class ScrapeResponse(BaseModel):
    content: str
    url: str


@router.post("/job-posting", response_model=ScrapeResponse)
async def scrape_job_posting_endpoint(
    request: ScrapeRequest,
    user=Depends(get_current_user),
):
    """Fetch and extract job posting content from URL."""
    content = await scrape_job_posting(str(request.url))
    return ScrapeResponse(content=content, url=str(request.url))
