from fastapi import APIRouter, Depends

from src.api.deps import get_job_service
from src.core.security import CurrentUser, get_current_user
from src.schemas.job import AnalysisJobOut, DetectedPlayerOut, PlayerLinkRequest
from src.services.job_service import JobService

router = APIRouter(prefix="/videos/{video_id}", tags=["processamento"])


@router.get("/job", response_model=AnalysisJobOut)
def get_job_status(video_id: str, service: JobService = Depends(get_job_service)):
    return service.get_status(video_id)


@router.get("/players", response_model=list[DetectedPlayerOut])
def list_detected_players(video_id: str, service: JobService = Depends(get_job_service)):
    """Lista os tracks anônimos ("Jogador A", "Jogador B"...) detectados no
    vídeo, para a tela de revisão/associação manual com atletas cadastrados."""
    return service.list_detected_players(video_id)


@router.post("/players/{detected_player_id}/link", response_model=DetectedPlayerOut)
def link_player(
    video_id: str,
    detected_player_id: str,
    payload: PlayerLinkRequest,
    user: CurrentUser = Depends(get_current_user),
    service: JobService = Depends(get_job_service),
):
    return service.link_player_to_athlete(detected_player_id, payload.athlete_id, user.id)
