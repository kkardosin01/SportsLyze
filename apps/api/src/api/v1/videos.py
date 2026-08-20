from fastapi import APIRouter, Depends

from src.api.deps import get_video_service
from src.core.security import CurrentUser, get_current_user
from src.schemas.video import (
    MatchCreate,
    MatchOut,
    UploadCompleteRequest,
    UploadInitiateRequest,
    UploadInitiateResponse,
    VideoOut,
)
from src.services.video_service import VideoService

router = APIRouter(prefix="/videos", tags=["videos"])
matches_router = APIRouter(prefix="/matches", tags=["partidas"])


@matches_router.post("", response_model=MatchOut, status_code=201)
def create_match(
    payload: MatchCreate,
    club_id: str | None = None,
    user: CurrentUser = Depends(get_current_user),
    service: VideoService = Depends(get_video_service),
):
    return service.create_match(user.id, club_id, payload)


@router.post("/upload/initiate", response_model=UploadInitiateResponse)
def initiate_upload(
    payload: UploadInitiateRequest,
    club_id: str | None = None,
    user: CurrentUser = Depends(get_current_user),
    service: VideoService = Depends(get_video_service),
):
    video, upload_url = service.initiate_upload(user.id, club_id, payload)
    return UploadInitiateResponse(
        video_id=video["id"],
        upload_url=upload_url,
        storage_path=video["storage_path"],
        max_upload_size_bytes=service._settings.max_upload_size_bytes,
    )


@router.post("/upload/complete", response_model=VideoOut)
def complete_upload(
    payload: UploadCompleteRequest,
    service: VideoService = Depends(get_video_service),
):
    """Chamado pelo client após o upload TUS terminar. Valida os metadados
    finais e enfileira o job de processamento no worker (nunca processa
    de forma síncrona na request)."""
    return service.complete_upload(payload)


@router.get("/{video_id}", response_model=VideoOut)
def get_video(
    video_id: str,
    user: CurrentUser = Depends(get_current_user),
    service: VideoService = Depends(get_video_service),
):
    return service.get_video(video_id, user.id)
