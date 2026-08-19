from datetime import datetime, timezone

from fastapi import HTTPException, status

from src.repositories.clubs import AthleteRepository
from src.repositories.videos import AnalysisJobRepository, DetectedPlayerRepository, VideoRepository


class JobService:
    def __init__(
        self,
        job_repo: AnalysisJobRepository,
        video_repo: VideoRepository,
        player_repo: DetectedPlayerRepository,
        athlete_repo: AthleteRepository,
    ):
        self._jobs = job_repo
        self._videos = video_repo
        self._players = player_repo
        self._athletes = athlete_repo

    def get_status(self, video_id: str) -> dict:
        job = self._jobs.get_latest_for_video(video_id)
        if job is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Nenhum job de análise encontrado para este vídeo.")
        return job

    def list_detected_players(self, video_id: str) -> list[dict]:
        return self._players.list_for_video(video_id)

    def link_player_to_athlete(self, detected_player_id: str, athlete_id: str, user_id: str) -> dict:
        athlete = self._athletes.get_by_id(athlete_id)
        if athlete is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Atleta não encontrado.")

        return self._players.update(
            detected_player_id,
            {
                "athlete_id": athlete_id,
                "linked_by_user_id": user_id,
                "linked_at": datetime.now(timezone.utc).isoformat(),
            },
        )
