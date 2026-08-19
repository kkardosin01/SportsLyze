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


class PlayerMatchStatsOut(BaseModel):
    id: str
    video_id: str
    match_id: str | None
    detected_player_id: str
    athlete_id: str | None
    touches: int
    passes_completed: int
    passes_attempted: int
    dribbles_successful: int
    dribbles_attempted: int
    fouls_committed: int
    fouls_suffered: int
    shots: int
    distance_km: float | None
    avg_speed_kmh: float | None
    max_speed_kmh: float | None
    heatmap: list[list[int]] | None
