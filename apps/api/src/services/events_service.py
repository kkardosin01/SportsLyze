from fastapi import HTTPException, status

from src.repositories.clubs import ClubMemberRepository
from src.repositories.videos import EventRepository, VideoRepository
from src.services.storage import StorageService


class EventsService:
    """Leitura de eventos detectados automaticamente no vídeo (heurísticas
    sobre o tracking, ver `sportslyze_cv.events.EventDetector`) e dos
    clipes cortados para cada um. Fase 2 detecta passe, drible,
    triangulação, finalização e falta — "desarme" e "jogada ensaiada"
    ficam reservados para um próximo incremento do mesmo detector (exigem
    classificação de time, ainda não implementada)."""

    def __init__(
        self,
        video_repo: VideoRepository,
        event_repo: EventRepository,
        member_repo: ClubMemberRepository,
        storage: StorageService,
    ):
        self._videos = video_repo
        self._events = event_repo
        self._members = member_repo
        self._storage = storage

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

    def list_events(self, video_id: str, user_id: str) -> list[dict]:
        self._get_video_with_access(video_id, user_id)
        events = self._events.list_for_video(video_id)
        for event in events:
            for clip in event.get("clips") or []:
                clip["playback_url"] = self._storage.create_signed_clip_url(clip["storage_path"])
        return events
