from celery import Celery
from fastapi import HTTPException, status

from src.repositories.clubs import AthleteRepository, ClubMemberRepository
from src.repositories.reports import ReportRepository
from src.repositories.videos import MatchRepository
from src.services.storage import StorageService


class ReportService:
    """Solicitação e listagem de relatórios de partida (PDF/slides/áudio,
    ver `reports.format`). A geração roda sempre no worker — este serviço só
    valida acesso, enfileira a task e resolve URLs assinadas de download."""

    def __init__(
        self,
        match_repo: MatchRepository,
        athlete_repo: AthleteRepository,
        member_repo: ClubMemberRepository,
        report_repo: ReportRepository,
        storage: StorageService,
        celery_client: Celery,
    ):
        self._matches = match_repo
        self._athletes = athlete_repo
        self._members = member_repo
        self._reports = report_repo
        self._storage = storage
        self._celery = celery_client

    def _ensure_match_access(self, match_id: str, user_id: str) -> dict:
        match = self._matches.get_by_id(match_id)
        if match is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Partida não encontrada.")

        if match.get("club_id"):
            if self._members.find_membership(match["club_id"], user_id) is not None:
                return match
        elif match.get("athlete_id"):
            athlete = self._athletes.get_by_id(match["athlete_id"])
            if athlete is not None and athlete.get("user_id") == user_id:
                return match

        raise HTTPException(status.HTTP_403_FORBIDDEN, "Sem acesso a esta partida.")

    def request_report(self, match_id: str, user_id: str, report_format: str) -> None:
        self._ensure_match_access(match_id, user_id)
        self._celery.send_task("tasks.generate_match_report", args=[match_id, user_id, report_format])

    def list_reports(self, match_id: str, user_id: str) -> list[dict]:
        self._ensure_match_access(match_id, user_id)
        reports = self._reports.list_for_match(match_id)
        for report in reports:
            report["download_url"] = self._storage.create_signed_report_url(report["storage_path"])
        return reports
