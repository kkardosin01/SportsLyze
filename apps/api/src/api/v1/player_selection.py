from fastapi import APIRouter, Depends, status

from src.api.deps import get_player_selection_service
from src.core.security import CurrentUser, get_current_user
from src.schemas.player_selection import (
    ReferenceFrameOut,
    SelectionHintCreate,
    SelectionHintOut,
)
from src.services.player_selection_service import PlayerSelectionService

router = APIRouter(prefix="/videos/{video_id}", tags=["selecao-manual"])


@router.post("/reference-frame", status_code=status.HTTP_202_ACCEPTED)
def request_reference_frame(
    video_id: str,
    user: CurrentUser = Depends(get_current_user),
    service: PlayerSelectionService = Depends(get_player_selection_service),
):
    """Dispara a extração assíncrona de um frame de referência do vídeo, para
    o coach marcar visualmente um jogador antes da análise completa."""
    service.request_reference_frame(video_id, user.id)


@router.get("/reference-frame", response_model=ReferenceFrameOut)
def get_reference_frame(
    video_id: str,
    user: CurrentUser = Depends(get_current_user),
    service: PlayerSelectionService = Depends(get_player_selection_service),
):
    return service.get_reference_frame(video_id, user.id)


@router.get("/selection-hints", response_model=list[SelectionHintOut])
def list_selection_hints(
    video_id: str,
    user: CurrentUser = Depends(get_current_user),
    service: PlayerSelectionService = Depends(get_player_selection_service),
):
    return service.list_hints(video_id, user.id)


@router.post("/selection-hints", response_model=SelectionHintOut)
def create_selection_hint(
    video_id: str,
    payload: SelectionHintCreate,
    user: CurrentUser = Depends(get_current_user),
    service: PlayerSelectionService = Depends(get_player_selection_service),
):
    """Marca visualmente um atleta já cadastrado numa posição do frame de
    referência. Não substitui número de camisa como identidade — é apenas um
    prior espacial que o worker usa para pré-vincular o track correspondente."""
    return service.create_hint(video_id, user.id, payload)


@router.delete("/selection-hints/{athlete_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_selection_hint(
    video_id: str,
    athlete_id: str,
    user: CurrentUser = Depends(get_current_user),
    service: PlayerSelectionService = Depends(get_player_selection_service),
):
    service.delete_hint(video_id, user.id, athlete_id)
