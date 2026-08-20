from fastapi import APIRouter

from src.api.v1.clubs import router as clubs_router
from src.api.v1.jobs import router as jobs_router
from src.api.v1.notifications import router as notifications_router
from src.api.v1.player_selection import router as player_selection_router
from src.api.v1.reports import router as reports_router
from src.api.v1.videos import matches_router, router as videos_router

api_router = APIRouter()
api_router.include_router(clubs_router)
api_router.include_router(videos_router)
api_router.include_router(matches_router)
api_router.include_router(jobs_router)
api_router.include_router(player_selection_router)
api_router.include_router(notifications_router)
api_router.include_router(reports_router)
