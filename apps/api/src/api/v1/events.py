from fastapi import APIRouter, Depends

from src.api.deps import get_events_service
from src.core.security import CurrentUser, get_current_user
from src.schemas.job import EventOut
from src.services.events_service import EventsService

router = APIRouter(prefix="/videos/{video_id}", tags=["eventos"])


@router.get("/events", response_model=list[EventOut])
def list_events(
    video_id: str,
    user: CurrentUser = Depends(get_current_user),
    service: EventsService = Depends(get_events_service),
):
    """Lista os eventos detectados automaticamente no vídeo (heurística de
    posse de bola), com os clipes já cortados para cada um, se disponíveis."""
    return service.list_events(video_id, user.id)
