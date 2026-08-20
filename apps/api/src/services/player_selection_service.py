from datetime import UTC, datetime

from celery import Celery
from fastapi import HTTPException, status

from src.repositories.clubs import AthleteRepository, ClubMemberRepository
from src.repositories.videos import (
    PlayerSelectionHintRepository,
    VideoReferenceFrameRepository,
    VideoRepository,
)
from src.schemas.player_selection import SelectionHintCreate
from src.services.storage import StorageService


class PlayerSelectionService:
    """Seleção manual de jogador no vídeo: extrai um frame de referência e
    guarda a marcação (bbox) que o coach desenhou sobre ele, associando um
    atleta já cadastrado a uma posição visual — nunca a um número de camisa.
    O worker usa essa marcação como prior espacial ao rodar o tracking (ver
    `sportslyze_cv.pipeline._resolve_hints`), pré-vinculando o track
    correspondente sem esperar a revisão manual pós-análise."""

    def __init__(
        self,
        video_repo: VideoRepository,
        frame_repo: VideoReferenceFrameRepository,
        hint_repo: PlayerSelectionHintRepository,
        athlete_repo: AthleteRepository,
        member_repo: ClubMemberRepository,
        storage: StorageService,
        celery_client: Celery,
    ):
        self._videos = video_repo
        self._frames = frame_repo
        self._hints = hint_repo
        self._athletes = athlete_repo
        self._members = member_repo
        self._storage = storage
        self._celery = celery_client

    def _get_video_with_access(self, video_id: str, user_id: str) -> dict:
        video = self._videos.get_by_id(video_id)
        if video is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Vídeo não encontrado.")

        if video["owner_type"] == "club":
            if self._members.find_membership(video["owner_id"], user_id) is None:
                raise HTTPException(status.HTTP_403_FORBIDDEN, "Sem acesso a este vídeo.")
        elif video["owner_id"] != user_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Sem acesso a este vídeo.")

        return video

    def request_reference_frame(self, video_id: str, user_id: str) -> None:
        self._get_video_with_access(video_id, user_id)
        self._celery.send_task("tasks.extract_reference_frame", args=[video_id, user_id])

    def get_reference_frame(self, video_id: str, user_id: str) -> dict:
        self._get_video_with_access(video_id, user_id)
        frame = self._frames.get_for_video(video_id)
        if frame is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                "Frame de referência ainda não extraído — solicite a extração antes.",
            )
        frame = dict(frame)
        frame["image_url"] = self._storage.create_signed_reference_frame_url(frame["storage_path"])
        return frame

    def list_hints(self, video_id: str, user_id: str) -> list[dict]:
        self._get_video_with_access(video_id, user_id)
        return self._hints.list_for_video(video_id)

    def create_hint(self, video_id: str, user_id: str, payload: SelectionHintCreate) -> dict:
        self._get_video_with_access(video_id, user_id)
        athlete = self._athletes.get_by_id(payload.athlete_id)
        if athlete is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Atleta não encontrado.")

        return self._hints.upsert(
            {
                "video_id": video_id,
                "athlete_id": payload.athlete_id,
                "timestamp_ms": payload.timestamp_ms,
                "bbox_x1": payload.bbox_x1,
                "bbox_y1": payload.bbox_y1,
                "bbox_x2": payload.bbox_x2,
                "bbox_y2": payload.bbox_y2,
                "frame_width": payload.frame_width,
                "frame_height": payload.frame_height,
                "created_by": user_id,
                "created_at": datetime.now(UTC).isoformat(),
            }
        )

    def delete_hint(self, video_id: str, user_id: str, athlete_id: str) -> None:
        self._get_video_with_access(video_id, user_id)
        self._hints.delete_for_athlete(video_id, athlete_id)
