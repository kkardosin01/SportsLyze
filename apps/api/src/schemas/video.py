from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class UploadInitiateRequest(BaseModel):
    match_id: str | None = None
    video_type: Literal["propria_equipe", "adversario"]
    original_filename: str
    size_bytes: int
    codec: str | None = None


class UploadInitiateResponse(BaseModel):
    video_id: str
    upload_url: str
    storage_path: str
    max_upload_size_bytes: int


class UploadCompleteRequest(BaseModel):
    video_id: str
    duration_seconds: int
    codec: str


class VideoOut(BaseModel):
    id: str
    owner_type: Literal["club", "athlete"]
    owner_id: str
    match_id: str | None
    video_type: Literal["propria_equipe", "adversario"]
    original_filename: str
    duration_seconds: int | None
    size_bytes: int | None
    retention_days: int
    original_deleted_at: datetime | None
    created_at: datetime


class MatchCreate(BaseModel):
    team_id: str | None = None
    athlete_id: str | None = None
    opponent_name: str | None = None
    match_date: str | None = None
    competition: str | None = None
    location: str | None = None


class MatchOut(BaseModel):
    id: str
    club_id: str | None
    team_id: str | None
    athlete_id: str | None
    opponent_name: str | None
    match_date: str | None
    competition: str | None
    location: str | None
    created_at: datetime
