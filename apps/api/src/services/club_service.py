from fastapi import HTTPException, status

from src.repositories.clubs import (
    AthleteRepository,
    ClubMemberRepository,
    ClubRepository,
    TeamRepository,
)
from src.schemas.club import ClubCreate
from src.schemas.team import AthleteCreate, TeamCreate


class ClubService:
    def __init__(
        self,
        club_repo: ClubRepository,
        member_repo: ClubMemberRepository,
        team_repo: TeamRepository,
        athlete_repo: AthleteRepository,
    ):
        self._clubs = club_repo
        self._members = member_repo
        self._teams = team_repo
        self._athletes = athlete_repo

    def create_club(self, payload: ClubCreate, admin_user_id: str) -> dict:
        email_domain = payload.admin_email.split("@")[-1].lower()
        if email_domain != payload.official_email_domain.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O e-mail do administrador precisa pertencer ao domínio oficial do clube.",
            )

        club = self._clubs.create(
            {
                "name": payload.name,
                "official_email_domain": payload.official_email_domain,
            }
        )
        self._members.create(
            {
                "club_id": club["id"],
                "user_id": admin_user_id,
                "role": "coordenador",
            }
        )
        return club

    def ensure_membership(self, club_id: str, user_id: str) -> dict:
        membership = self._members.find_membership(club_id, user_id)
        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem acesso a este clube.",
            )
        return membership

    def create_team(self, club_id: str, user_id: str, payload: TeamCreate) -> dict:
        self.ensure_membership(club_id, user_id)
        return self._teams.create({"club_id": club_id, "name": payload.name, "season": payload.season})

    def create_athlete(self, club_id: str, user_id: str, payload: AthleteCreate) -> dict:
        self.ensure_membership(club_id, user_id)
        return self._athletes.create(
            {
                "club_id": club_id,
                "team_id": payload.team_id,
                "full_name": payload.full_name,
                "birth_date": payload.birth_date.isoformat() if payload.birth_date else None,
                "position": payload.position,
                "jersey_number": payload.jersey_number,
            }
        )

    def list_my_clubs(self, user_id: str) -> list[dict]:
        return self._members.list_by_user(user_id)

    def list_athletes(self, club_id: str, user_id: str) -> list[dict]:
        self.ensure_membership(club_id, user_id)
        return self._athletes.list({"club_id": club_id})
