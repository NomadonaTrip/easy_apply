from fastapi import APIRouter

from app.api.v1 import auth, roles, experience, resumes, applications, scrape, sse_test, research, generation


api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(roles.router)
api_router.include_router(experience.router)
api_router.include_router(resumes.router)
api_router.include_router(applications.router)
api_router.include_router(scrape.router)
api_router.include_router(sse_test.router)  # Temporary: SSE spike (Story 0-5)
api_router.include_router(research.router)
api_router.include_router(generation.router)
