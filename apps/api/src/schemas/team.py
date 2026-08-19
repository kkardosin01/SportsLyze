from datetime import date, datetime

from pydantic import BaseModel


class TeamCreate(BaseModel):
    name: str
    season: str | None = None


class TeamOut(BaseModel):
    id: str
    club_id: str
    name: str
    season: str | None
    created_at: datetime


class AthleteCreate(BaseModel):
    team_id: str | None = None
    full_name: str
    birth_date: date | None = None
    position: str | None = None
    jersey_number: int | None = None


class AthleteOut(BaseModel):
    id: str
    club_id: str | None
    team_id: str | None
    user_id: str | None
    full_name: str
    birth_date: date | None
    position: str | None
    jersey_number: int | None
    created_at: datetime
