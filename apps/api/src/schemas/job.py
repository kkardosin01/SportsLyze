from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class AnalysisJobOut(BaseModel):
    id: str
    video_id: str
    status: Literal["queued", "processing", "done", "failed"]
    current_stage: str | None
    progress_pct: int
    error_message: str | None
    estimated_duration_seconds: int | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


class DetectedPlayerOut(BaseModel):
    id: str
    video_id: str
    track_id: int
    label: str
    ocr_jersey_number: int | None
    ocr_confidence: float | None
    thumbnail_path: str | None
    athlete_id: str | None
    linked_at: datetime | None


class PlayerLinkRequest(BaseModel):
    athlete_id: str
