from fastapi import APIRouter, Depends

from src.api.deps import get_club_service
from src.core.security import CurrentUser, get_current_user
from src.schemas.club import ClubCreate, ClubOut
from src.schemas.team import AthleteCreate, AthleteOut, TeamCreate, TeamOut
from src.services.club_service import ClubService

router = APIRouter(prefix="/clubs", tags=["clubes"])


@router.post("", response_model=ClubOut, status_code=201)
def create_club(
    payload: ClubCreate,
    user: CurrentUser = Depends(get_current_user),
    service: ClubService = Depends(get_club_service),
):
    return service.create_club(payload, admin_user_id=user.id)


@router.get("/me", response_model=list[dict])
def list_my_clubs(
    user: CurrentUser = Depends(get_current_user),
    service: ClubService = Depends(get_club_service),
):
    return service.list_my_clubs(user.id)


@router.post("/{club_id}/teams", response_model=TeamOut, status_code=201)
def create_team(
    club_id: str,
    payload: TeamCreate,
    user: CurrentUser = Depends(get_current_user),
    service: ClubService = Depends(get_club_service),
):
    return service.create_team(club_id, user.id, payload)


@router.post("/{club_id}/athletes", response_model=AthleteOut, status_code=201)
def create_athlete(
    club_id: str,
    payload: AthleteCreate,
    user: CurrentUser = Depends(get_current_user),
    service: ClubService = Depends(get_club_service),
):
    return service.create_athlete(club_id, user.id, payload)
