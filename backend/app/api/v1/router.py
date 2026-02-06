from fastapi import APIRouter

from app.api.v1 import auth, roles, experience, resumes, applications, scrape


api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(roles.router)
api_router.include_router(experience.router)
api_router.include_router(resumes.router)
api_router.include_router(applications.router)
api_router.include_router(scrape.router)
