from celery import Celery
from fastapi import HTTPException, status

from src.core.config import Settings
from src.repositories.clubs import AthleteRepository, ClubMemberRepository
from src.repositories.videos import (
    AnalysisJobRepository,
    MatchRepository,
    VideoRepository,
)
from src.schemas.video import MatchCreate, UploadCompleteRequest, UploadInitiateRequest
from src.services.storage import StorageService


class VideoService:
    def __init__(
        self,
        video_repo: VideoRepository,
        match_repo: MatchRepository,
        job_repo: AnalysisJobRepository,
        member_repo: ClubMemberRepository,
        athlete_repo: AthleteRepository,
        storage: StorageService,
        celery_client: Celery,
        settings: Settings,
    ):
        self._videos = video_repo
        self._matches = match_repo
        self._jobs = job_repo
        self._members = member_repo
        self._athletes = athlete_repo
        self._storage = storage
        self._celery = celery_client
        self._settings = settings

    def _resolve_owner(self, user_id: str, club_id: str | None, athlete_id: str | None) -> tuple[str, str]:
        """Determina owner_type/owner_id validando que o usuário tem permissão."""
        if club_id:
            if self._members.find_membership(club_id, user_id) is None:
                raise HTTPException(status.HTTP_403_FORBIDDEN, "Sem acesso a este clube.")
            return "club", club_id

        # Fluxo do atleta independente: owner é o próprio usuário
        return "athlete", user_id

    def create_match(self, user_id: str, club_id: str | None, payload: MatchCreate) -> dict:
        if club_id is None and payload.athlete_id is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "Informe club_id ou athlete_id para criar a partida."
            )
        if club_id:
            if self._members.find_membership(club_id, user_id) is None:
                raise HTTPException(status.HTTP_403_FORBIDDEN, "Sem acesso a este clube.")
        return self._matches.create(
            {
                "club_id": club_id,
                "team_id": payload.team_id,
                "athlete_id": payload.athlete_id,
                "created_by": user_id,
                "opponent_name": payload.opponent_name,
                "match_date": payload.match_date,
                "competition": payload.competition,
                "location": payload.location,
            }
        )

    def initiate_upload(
        self, user_id: str, club_id: str | None, payload: UploadInitiateRequest
    ) -> tuple[dict, str]:
        extension = "." + payload.original_filename.rsplit(".", 1)[-1].lower()
        if extension not in self._settings.allowed_video_extensions:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Formato não suportado. Apenas {', '.join(self._settings.allowed_video_extensions)}.",
            )
        if payload.size_bytes > self._settings.max_upload_size_bytes:
            max_gb = self._settings.max_upload_size_bytes / (1024**3)
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, f"Vídeo excede o limite de {max_gb:.0f} GB."
            )

        owner_type, owner_id = self._resolve_owner(user_id, club_id, None)
        storage_path = self._storage.build_video_path(owner_type, owner_id, payload.original_filename)

        video = self._videos.create(
            {
                "owner_type": owner_type,
                "owner_id": owner_id,
                "match_id": payload.match_id,
                "video_type": payload.video_type,
                "storage_path": storage_path,
                "original_filename": payload.original_filename,
                "size_bytes": payload.size_bytes,
                "codec": payload.codec,
                "uploaded_by": user_id,
                "retention_days": self._settings.video_retention_days_default,
            }
        )
        upload_url = self._storage.create_resumable_upload_url(storage_path)
        return video, upload_url

    def get_video(self, video_id: str, user_id: str) -> dict:
        video = self._videos.get_by_id(video_id)
        if video is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Vídeo não encontrado.")

        if video["owner_type"] == "club":
            if self._members.find_membership(video["owner_id"], user_id) is None:
                raise HTTPException(status.HTTP_403_FORBIDDEN, "Sem acesso a este vídeo.")
        elif video["owner_id"] != user_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Sem acesso a este vídeo.")

        return video

    def complete_upload(self, payload: UploadCompleteRequest) -> dict:
        video = self._videos.get_by_id(payload.video_id)
        if video is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Vídeo não encontrado.")

        if payload.codec not in ("h264", "hevc"):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Codec de vídeo não suportado (use H.264 ou HEVC).",
            )

        video = self._videos.update(
            payload.video_id,
            {"duration_seconds": payload.duration_seconds, "codec": payload.codec},
        )

        job = self._jobs.create(
            {
                "video_id": payload.video_id,
                "status": "queued",
                "estimated_duration_seconds": payload.duration_seconds * 2,
            }
        )

        self._celery.send_task("tasks.process_video", args=[payload.video_id, job["id"]])
        return video
