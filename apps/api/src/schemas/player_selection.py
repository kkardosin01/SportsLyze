from datetime import datetime

from pydantic import BaseModel, Field


class ReferenceFrameOut(BaseModel):
    id: str
    video_id: str
    storage_path: str
    image_url: str
    timestamp_ms: int
    frame_width: int
    frame_height: int
    created_at: datetime


class SelectionHintCreate(BaseModel):
    athlete_id: str
    timestamp_ms: int = Field(ge=0)
    bbox_x1: float = Field(ge=0)
    bbox_y1: float = Field(ge=0)
    bbox_x2: float = Field(gt=0)
    bbox_y2: float = Field(gt=0)
    frame_width: int = Field(gt=0)
    frame_height: int = Field(gt=0)


class SelectionHintOut(BaseModel):
    id: str
    video_id: str
    athlete_id: str
    timestamp_ms: int
    bbox_x1: float
    bbox_y1: float
    bbox_x2: float
    bbox_y2: float
    frame_width: int
    frame_height: int
    created_by: str
    created_at: datetime
