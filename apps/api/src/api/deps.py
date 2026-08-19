from fastapi import Depends
from supabase import Client

from src.core.celery_client import get_celery_client
from src.core.config import Settings, get_settings
from src.core.security import CurrentUser, get_current_user
from src.db.session import get_supabase_admin
from src.repositories.clubs import AthleteRepository, ClubMemberRepository, ClubRepository, TeamRepository
from src.repositories.videos import (
    AnalysisJobRepository,
    DetectedPlayerRepository,
    MatchRepository,
    NotificationRepository,
    PlayerMatchStatsRepository,
    VideoRepository,
)
from src.services.club_service import ClubService
from src.services.job_service import JobService
from src.services.notification_service import NotificationService
from src.services.storage import StorageService
from src.services.video_service import VideoService


def get_db() -> Client:
    return get_supabase_admin()


def get_club_service(db: Client = Depends(get_db)) -> ClubService:
    return ClubService(
        ClubRepository(db), ClubMemberRepository(db), TeamRepository(db), AthleteRepository(db)
    )


def get_video_service(
    db: Client = Depends(get_db), settings: Settings = Depends(get_settings)
) -> VideoService:
    return VideoService(
        VideoRepository(db),
        MatchRepository(db),
        AnalysisJobRepository(db),
        ClubMemberRepository(db),
        AthleteRepository(db),
        StorageService(db),
        get_celery_client(),
        settings,
    )


def get_job_service(db: Client = Depends(get_db)) -> JobService:
    return JobService(
        AnalysisJobRepository(db),
        VideoRepository(db),
        DetectedPlayerRepository(db),
        AthleteRepository(db),
        PlayerMatchStatsRepository(db),
    )


def get_notification_service(db: Client = Depends(get_db)) -> NotificationService:
    return NotificationService(NotificationRepository(db))


CurrentUserDep = Depends(get_current_user)

__all__ = ["CurrentUser", "get_current_user", "CurrentUserDep"]
